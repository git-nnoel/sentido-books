"""Thin external API wrappers for ingestion.

Phase 0 ships only the Open Library client. The Google Books fallback
is deferred to Phase 1 per plan §9 deliverable list — when Open Library
returns nothing in Phase 0 the service raises 404.

These clients sit at the I/O boundary (plan §3.2 / skill §3.2). The
shared :class:`httpx.AsyncClient` is built once at app startup
(``main.lifespan``) and stashed on ``app.state.httpx_client``. Routes
pull it via ``request.app.state.httpx_client`` and hand it to
ingestion's service, which constructs the client wrapper per call.

The User-Agent header (plan §7.2, mandatory by Open Library policy)
lives on the shared httpx client (see ``shared.http.make_client``), so
each request inherits it automatically.
"""

from __future__ import annotations

from typing import Any

import httpx

_OPEN_LIBRARY_API = "https://openlibrary.org/api/books"


class OpenLibraryClient:
    """Wraps Open Library's ``api/books?jscmd=data`` endpoint.

    A new instance is created per ingest call (it's just a thin handle
    around the shared httpx client); no per-request state beyond the
    underlying client.
    """

    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

    async def fetch_by_isbn(self, isbn: str) -> dict[str, Any] | None:
        """Return the inner book dict for ``isbn``, or ``None`` if Open
        Library has no record.

        The response shape is::

            { "ISBN:9788501062451": { ... book fields ... } }

        We pluck the inner dict at ``ISBN:{isbn}``. Open Library
        responds 200 + ``{}`` when an ISBN is unknown — we treat that
        as a not-found and return ``None``. A 404 also returns
        ``None``. Any other network/HTTP error propagates; the service
        translates it into an ``ApiError`` for the route layer.
        """
        params = {
            "bibkeys": f"ISBN:{isbn}",
            "format": "json",
            "jscmd": "data",
        }
        response = await self._http.get(_OPEN_LIBRARY_API, params=params)

        if response.status_code == 404:
            return None
        response.raise_for_status()

        payload = response.json()
        if not isinstance(payload, dict) or not payload:
            return None

        inner = payload.get(f"ISBN:{isbn}")
        if not isinstance(inner, dict) or not inner:
            return None
        return inner
