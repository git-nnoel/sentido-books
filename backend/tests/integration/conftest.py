"""Integration-test fixtures.

**Test-DB strategy (decided in B3).**

We run integration tests against the same Postgres container that
``docker/docker-compose.yml`` starts for development, but in a
**separate database** named ``sentido_test``. Rationale, weighed
against the alternatives:

- **Why not testcontainers?** It pulls a fresh image per process and
  needs Docker Python bindings, which adds friction for solo-developer
  iteration. The dev container is already running for normal work.
- **Why not the dev DB directly?** Integration tests truncate tables;
  the curator's real data would vanish on every run.
- **Why a separate database, not a separate schema?** pgvector
  extensions are per-database in Postgres. Cleanly tearing down a
  schema would still leave the extension on the dev DB.

Bootstrapping (idempotent, runs once per pytest session):
  1. Connect to the maintenance DB (``postgres``) as the ``sentido``
     role and ``CREATE DATABASE sentido_test`` if missing.
  2. Connect to ``sentido_test`` and ``CREATE EXTENSION IF NOT EXISTS
     vector`` + ``pgcrypto``.
  3. Drop + recreate all ORM tables via ``Base.metadata`` rather than
     running Alembic. This keeps tests fast and removes Alembic from
     the test path; Alembic itself is covered by the
     ``alembic upgrade head`` smoke step in the verification commands.

A single ``test_session`` fixture is exposed to integration tests. It
yields an ``AsyncSession`` bound to the test DB; the fixture rolls
back any uncommitted work and truncates the catalog tables between
tests so each test starts from a clean slate.

Future tasks (B4, B5) reuse this exact fixture without modification.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Final

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Side-effect imports — required so Base.metadata sees every table.
import sentido.catalog.models  # noqa: F401
import sentido.search.models  # noqa: F401
from sentido.shared.db import Base

TEST_DB_NAME: Final = "sentido_test"


def _admin_url() -> str:
    """URL pointing at the maintenance ``postgres`` DB on the dev host.

    Derived from the configured ``DATABASE_URL`` so we never hardcode
    credentials in the test harness. The conftest at the repo root
    sets a default ``DATABASE_URL`` if none is present in the env.
    """
    base = os.environ["DATABASE_URL"]
    # Replace the database segment (anything after the last "/") with
    # "postgres" — the always-present maintenance database.
    head, _ = base.rsplit("/", 1)
    return f"{head}/postgres"


def _test_db_url() -> str:
    """The configured DATABASE_URL is already the test DB URL."""
    return os.environ["DATABASE_URL"]


async def _ensure_test_database_exists() -> None:
    """``CREATE DATABASE sentido_test`` if it does not already exist.

    Connects through the maintenance DB using AUTOCOMMIT — Postgres
    refuses ``CREATE DATABASE`` inside a transaction.
    """
    engine = create_async_engine(_admin_url(), isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            exists = await conn.scalar(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": TEST_DB_NAME},
            )
            if not exists:
                await conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    finally:
        await engine.dispose()


async def _enable_extensions(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))


async def _reset_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncIterator[AsyncEngine]:
    """Session-scoped async engine bound to ``sentido_test``."""
    await _ensure_test_database_exists()
    engine = create_async_engine(_test_db_url(), pool_pre_ping=True)
    await _enable_extensions(engine)
    await _reset_schema(engine)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Per-test async session. Tables are truncated between tests.

    We use ``TRUNCATE ... RESTART IDENTITY CASCADE`` rather than
    ``Base.metadata.drop_all`` per test because dropping/recreating
    tables on every test is ~10x slower for the same isolation.
    """

    async def _truncate(conn: AsyncConnection) -> None:
        # Order matters less under CASCADE but we list child tables
        # first for clarity. Catalog tables only — resonance_cache and
        # collections are exercised in later phases.
        await conn.execute(
            text(
                "TRUNCATE editions, collection_books, books, authors, "
                "collections, resonance_cache "
                "RESTART IDENTITY CASCADE"
            )
        )

    async with test_engine.begin() as conn:
        await _truncate(conn)

    sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session


# The repo-root tests/conftest.py sets ADMIN_TOKEN=test-admin-token before
# any sentido module is imported. Integration tests can therefore rely on
# that value directly; no per-test monkeypatching is needed.
ADMIN_TOKEN: Final = "test-admin-token"


@pytest.fixture
def admin_token() -> str:
    """Return the admin token expected by ``require_admin``.

    Sourced from the repo-root ``tests/conftest.py`` defaults so the
    test config and the auth dependency stay in sync.
    """
    return ADMIN_TOKEN
