"""Ingestion service — imperative shell for ISBN-based book ingestion.

Plan §3.2 / §3.3 (M3, M8): all HTTP calls (to Open Library) and DB
writes that ingestion needs live here. Pure data transformations live
in :mod:`sentido.ingestion.logic`. The catalog write path
(``catalog.service.create_book_from_normalized``) is the only place
this module reaches outside its own files; ingestion does not perform
its own SQL.

The Google Books fallback documented in plan §7.3 is deferred to
Phase 1 per plan §9 deliverable list. In Phase 0, when Open Library
returns nothing the service raises 404.
"""

from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.catalog import service as catalog_service
from sentido.catalog.models import BookORM
from sentido.ingestion.clients import OpenLibraryClient
from sentido.ingestion.logic import (
    normalize_isbn,
    normalize_open_library_response,
)
from sentido.shared.errors import ApiError


async def ingest_by_isbn(
    session: AsyncSession,
    http_client: httpx.AsyncClient,
    isbn_raw: str,
) -> BookORM:
    """End-to-end ingestion: normalize ISBN → Open Library → persist.

    Workflow:
        1. Normalize ``isbn_raw`` to digits-only (10 or 13 chars).
           Invalid input raises ``ValueError`` which the global handler
           turns into HTTP 400.
        2. Duplicate-check: if any edition already carries this ISBN,
           raise ``ApiError(409, "book already exists")``.
        3. Fetch from Open Library. A missing record raises
           ``ApiError(404, "isbn not found")``. A network/HTTP error is
           translated to ``ApiError(502, ...)`` so the route layer
           returns a Bad Gateway rather than leaking ``httpx``
           exceptions.
        4. Normalize the response. If the payload doesn't carry both a
           title and at least one author, raise
           ``ApiError(404, "book metadata incomplete")``.
        5. Persist via ``catalog.service.create_book_from_normalized``.
        6. Commit and return the persisted ``BookORM`` (with author +
           editions eager-loaded by the catalog helper).

    The admin route is responsible for converting the returned ORM to
    the ``AdminBookResponse`` shape — keeping API DTO concerns in
    ``admin/``.
    """
    isbn = normalize_isbn(isbn_raw)

    existing = await catalog_service.find_book_by_isbn(session, isbn)
    if existing is not None:
        raise ApiError(409, "book already exists")

    client = OpenLibraryClient(http_client)
    try:
        raw = await client.fetch_by_isbn(isbn)
    except httpx.HTTPError as exc:
        # Per skill R7/R8: infrastructure exceptions never reach the
        # route. We log nothing here yet — structured logging lands in
        # Phase 1 per plan §10. Translate to a 502 with a short detail.
        raise ApiError(502, f"open library request failed: {exc}") from exc

    if raw is None:
        raise ApiError(404, "isbn not found")

    normalized = normalize_open_library_response(raw, isbn)
    if normalized is None:
        raise ApiError(404, "book metadata incomplete")

    book = await catalog_service.create_book_from_normalized(session, normalized)
    await session.commit()
    return book
