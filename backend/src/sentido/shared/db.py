"""Async engine, session factory, and FastAPI `get_session` dependency.

Follows the backend-system-architecture skill §3.8 (Mode B canonical
example). The DeclarativeBase lives here so all module `models.py` files
share the same metadata — this is the single MetaData object Alembic
autogenerates against.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared SQLAlchemy 2.x declarative base.

    All ORM models across the service inherit from this class so they
    register on one MetaData instance — required for Alembic
    autogeneration to see every table.
    """


def make_engine(url: str) -> AsyncEngine:
    """Build the async engine. Called once at app startup (skill R6)."""
    return create_async_engine(url, pool_pre_ping=True)


def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build the async sessionmaker. Called once at app startup."""
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a per-request `AsyncSession`.

    The sessionmaker is built once in the app lifespan and stashed on
    `request.app.state.sessionmaker`. This dependency hands out one
    session per request and ensures it is closed afterward.
    """
    sessionmaker: async_sessionmaker[AsyncSession] = request.app.state.sessionmaker
    async with sessionmaker() as session:
        yield session
