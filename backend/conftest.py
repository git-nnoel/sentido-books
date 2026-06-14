"""Repo-wide pytest configuration.

Pytest discovers this file at the rootdir (``backend/``) and applies
it to every test, regardless of whether it lives under ``src/`` (module
unit + small-integration tests, plan §12) or ``tests/`` (cross-module
integration and e2e).

Two responsibilities, both moved here from ``tests/conftest.py`` and
``tests/integration/conftest.py`` so the same fixtures are visible to
module tests under ``src/sentido/<module>/tests/``:

1. **Environment bootstrap.** Required env vars are set *before* any
   ``sentido.*`` import so that
   :func:`sentido.shared.config.get_settings` (which is
   ``lru_cache``-backed and validates required fields at construction)
   can succeed in any test process.

2. **Database fixtures.** ``test_engine`` (session-scoped) and
   ``test_session`` (function-scoped) point at the ``sentido_test``
   database on the dev Postgres container. The integration test-DB
   strategy is documented at the bottom of this file and was
   originally drafted in B3.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Final

# ---------------------------------------------------------------------------
# 1. Environment bootstrap — must run before sentido.* imports below.
# ---------------------------------------------------------------------------
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://sentido:sentido@localhost:5433/sentido_test",
)
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
os.environ.setdefault("GOOGLE_BOOKS_API_KEY", "test-google-books-key")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")


# ---------------------------------------------------------------------------
# 2. Shared DB fixtures (rest of this file).
# ---------------------------------------------------------------------------
import pytest  # noqa: E402  (env must precede imports)
import pytest_asyncio  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Side-effect imports — required so Base.metadata sees every table when
# tests reset the schema via create_all.
import sentido.catalog.models  # noqa: F401, E402
import sentido.search.models  # noqa: F401, E402
from sentido.shared.db import Base  # noqa: E402

TEST_DB_NAME: Final = "sentido_test"


def _admin_url() -> str:
    """URL pointing at the maintenance ``postgres`` DB on the dev host.

    Derived from the configured ``DATABASE_URL`` so we never hardcode
    credentials in the test harness. The env defaults above set a
    sensible value if none is present in the environment.
    """
    base = os.environ["DATABASE_URL"]
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
    """Session-scoped async engine bound to ``sentido_test``.

    Bootstraps once per pytest session: ensures the DB exists, enables
    pgvector + pgcrypto, drops + recreates all ORM tables. Subsequent
    tests reuse the engine and rely on the ``test_session`` fixture to
    truncate catalog tables between tests.
    """
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

    ``TRUNCATE ... RESTART IDENTITY CASCADE`` is ~10x faster than
    dropping and recreating tables per test for the same isolation.
    """

    async def _truncate(conn: AsyncConnection) -> None:
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


ADMIN_TOKEN: Final = "test-admin-token"


@pytest.fixture
def admin_token() -> str:
    """Return the admin token expected by ``require_admin``.

    Matches the value set in the env bootstrap above so the test
    config and the auth dependency stay in sync.
    """
    return ADMIN_TOKEN
