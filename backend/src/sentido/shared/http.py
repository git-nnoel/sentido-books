"""Shared async httpx client factory.

A single `httpx.AsyncClient` is constructed at app startup (skill R6) by
the lifespan handler and stashed on `app.state.httpx_client`. Modules
that need to make outbound HTTP calls (`ingestion/clients.py`,
`generation/clients.py` in later tasks) receive the shared client via
`app.state`/`Depends()` rather than constructing their own.

Defaults applied here:

- 30s total timeout (plan §7.2 / §7.3 — external lookups should fail
  fast in v1 rather than hanging request threads).
- A configurable ``User-Agent`` header. Open Library requires a
  descriptive UA per plan §7.2; we set it once here so every outbound
  request inherits it.
"""

from __future__ import annotations

import httpx


def make_client(user_agent: str) -> httpx.AsyncClient:
    """Build the shared async HTTP client.

    Called once at app startup by the FastAPI lifespan handler.

    Args:
        user_agent: Value for the default ``User-Agent`` header. Sourced
            from ``settings.OPEN_LIBRARY_USER_AGENT``.

    Returns:
        An ``httpx.AsyncClient`` configured with a 30s total timeout and
        the supplied User-Agent. Closing is the caller's responsibility
        (the lifespan handler awaits ``aclose()`` on shutdown).
    """
    return httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        headers={"User-Agent": user_agent},
    )
