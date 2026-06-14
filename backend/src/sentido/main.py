"""FastAPI app factory for the Sentido backend.

Run locally with::

    uvicorn sentido.main:app --host 0.0.0.0 --port 8000

This module is intentionally thin — it composes the application:

- builds long-lived resources (engine, sessionmaker, httpx client,
  OpenAI client) once at startup via a ``lifespan`` handler and stashes
  them on ``app.state`` (skill R6),
- installs CORS middleware from settings (plan §8.1),
- registers exception handlers (translation lives in
  :mod:`sentido.shared.errors`),
- mounts each module's router,
- and serves the inline health endpoint (plan §5.3).

No business logic lives here. The factory pattern (``create_app``)
keeps the app constructible from tests without uvicorn.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from sentido.admin.routes import router as admin_router
from sentido.catalog.routes import router as catalog_router
from sentido.search.routes import router as search_router
from sentido.shared.config import get_settings
from sentido.shared.db import make_engine, make_sessionmaker
from sentido.shared.errors import register_exception_handlers
from sentido.shared.http import make_client

API_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Build shared resources once at startup; dispose them on shutdown.

    Per skill R6, anything expensive to construct (DB engine, HTTP
    client, OpenAI client, settings) lives on ``app.state`` for the
    lifetime of the process. Request-scoped dependencies read these
    instances; they never build their own.

    The ``openai_client`` is initialized here even though B2 does not
    use it yet — owning its lifetime in the lifespan means B3/B4 can
    pull it from ``app.state`` without changing startup wiring.
    """
    settings = get_settings()
    engine = make_engine(settings.DATABASE_URL)
    sessionmaker = make_sessionmaker(engine)
    httpx_client = make_client(settings.OPEN_LIBRARY_USER_AGENT)
    openai_client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL,
    )

    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    app.state.httpx_client = httpx_client
    app.state.openai_client = openai_client

    try:
        yield
    finally:
        # Order: outbound clients first, then DB engine. Each close is
        # awaited independently; we don't want one failure to skip the
        # others.
        try:
            await openai_client.close()
        finally:
            try:
                await httpx_client.aclose()
            finally:
                await engine.dispose()


def create_app() -> FastAPI:
    """Construct and return the configured FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Sentido API",
        version=API_VERSION,
        lifespan=lifespan,
    )

    # CORS — plan §8.1. Public and admin endpoints share the same CORS
    # config since the admin panel ships from the same Vercel domain.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Authorization", "Content-Type"],
    )

    register_exception_handlers(app)

    # Health — plan §5.3. One endpoint, no auth, no module needed.
    @app.get("/v1/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": API_VERSION}

    app.include_router(catalog_router)
    app.include_router(search_router)
    app.include_router(admin_router)

    return app


app = create_app()
