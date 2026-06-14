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

import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.catalog.models import BookORM
from sentido.generation import service as generation_service
from sentido.generation.clients import OpenAIClient
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


async def generate_book_artifacts(
    *,
    session: AsyncSession,
    openai_client: OpenAIClient,
    book_id: uuid.UUID,
    regenerate: bool,
) -> BookORM:
    """Run synopsis + emotional profile + embedding generation for a book.

    Thin passthrough to :func:`sentido.generation.service.generate_artifacts`
    — mirrors the :func:`ingest_book` pattern so the admin route stays
    the only entry point for curator workflows (plan §3.3 M4). Future
    extensions (auto-publish after approval, multi-step flows) hang
    off this admin function without touching the route.
    """
    return await generation_service.generate_artifacts(
        session=session,
        openai_client=openai_client,
        book_id=book_id,
        regenerate=regenerate,
    )
