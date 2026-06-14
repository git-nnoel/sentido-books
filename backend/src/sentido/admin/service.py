"""Admin workflow coordination — ingest → generate → publish.

Plan §3.3 M4: ``admin/`` is the composition root for curator workflows.
It may import from ``catalog``, ``ingestion``, ``generation`` and
``shared``. In Phase 0 only ingestion is wired through here; B4/B5 add
generate + publish steps to this module.

The split between ``admin.service.ingest_book`` and
``ingestion.service.ingest_by_isbn`` is intentional even when the
admin function is a passthrough: keeping the admin module as the only
caller of ingestion lets later phases extend the workflow (e.g.,
auto-trigger generation after ingest) without changing the route.
"""

from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.catalog.models import BookORM
from sentido.ingestion import service as ingestion_service


async def ingest_book(
    session: AsyncSession,
    http_client: httpx.AsyncClient,
    isbn: str,
) -> BookORM:
    """Ingest a book by ISBN via the ingestion module.

    Returns the persisted ``BookORM`` with ``author`` and ``editions``
    eager-loaded. The route is responsible for converting to
    :class:`sentido.admin.schemas.AdminBookResponse`.
    """
    return await ingestion_service.ingest_by_isbn(session, http_client, isbn)
