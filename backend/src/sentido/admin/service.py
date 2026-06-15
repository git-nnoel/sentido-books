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
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.catalog import service as catalog_service
from sentido.catalog.models import BookORM, CollectionORM
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


async def update_book(
    session: AsyncSession,
    book_id: uuid.UUID,
    patch: dict[str, Any],
) -> BookORM:
    """Apply a partial update to a book row (plan §5.2).

    Thin passthrough to :func:`sentido.catalog.service.update_book`.
    The admin module owns the workflow boundary so future curator
    actions (audit logging, post-update notifications) hang off this
    function without changing the route.
    """
    return await catalog_service.update_book(session, book_id, patch)


async def list_books(
    session: AsyncSession,
    *,
    status_filter: str,
    limit: int,
    offset: int,
) -> tuple[list[BookORM], int]:
    """List books with admin filters (plan §5.2).

    Thin passthrough to :func:`sentido.catalog.service.list_admin_books`
    — the admin module stays the only entry point for curator workflows
    (plan §3.3 M4) so future extensions (audit logging, additional
    filters) hang off this function without changing the route.
    """
    return await catalog_service.list_admin_books(
        session,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


async def publish_book(session: AsyncSession, book_id: uuid.UUID) -> BookORM:
    """Approve + publish a book in one call (plan §5.2).

    Equivalent to ``PUT /v1/admin/books/{id}`` with body
    ``{"profile_status": "approved", "published": true}``. The publish
    gate inside :func:`sentido.catalog.service.update_book` enforces
    that ``embedding_status == "done"``; if the embedding is still
    pending the call returns 422 (the gate uses the post-patch state,
    so a single PATCH approving + publishing is allowed when the
    embedding is already present).
    """
    return await catalog_service.update_book(
        session,
        book_id,
        {"profile_status": "approved", "published": True},
    )


# ---------------------------------------------------------------------------
# Collections — thin passthrough wrappers (plan §14.2 / §14.5)
# ---------------------------------------------------------------------------
#
# Each wrapper mirrors the ingest/generate/update pattern above: the
# admin module stays the only entry point for curator workflows (M4) so
# future extensions (audit logging, notifications) hang off these
# functions without changing the routes. The catalog service owns the
# queries and transactions (M8).


async def create_collection(
    session: AsyncSession,
    *,
    title: str,
    description: str | None,
) -> CollectionORM:
    """Create an editorial collection (plan §14.2)."""
    return await catalog_service.create_collection(
        session, title=title, description=description
    )


async def update_collection(
    session: AsyncSession,
    collection_id: uuid.UUID,
    patch: dict[str, Any],
) -> CollectionORM:
    """Partial update of a collection (plan §14.2)."""
    return await catalog_service.update_collection(session, collection_id, patch)


async def delete_collection(
    session: AsyncSession, collection_id: uuid.UUID
) -> None:
    """Delete a collection; cascades to its book links (plan §14.2)."""
    await catalog_service.delete_collection(session, collection_id)


async def list_collections(
    session: AsyncSession,
    *,
    status_filter: str,
    limit: int,
    offset: int,
) -> tuple[list[CollectionORM], int]:
    """List collections with a status filter (plan §14.2)."""
    return await catalog_service.list_admin_collections(
        session,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


async def get_collection(
    session: AsyncSession, collection_id: uuid.UUID
) -> CollectionORM:
    """Load a collection (all books, incl. unpublished — D10) (plan §14.2)."""
    return await catalog_service.get_collection_for_admin(session, collection_id)


async def replace_collection_books(
    session: AsyncSession,
    collection_id: uuid.UUID,
    book_ids: list[uuid.UUID],
) -> CollectionORM:
    """Replace the ordered book list in one transaction (plan §14.2)."""
    return await catalog_service.replace_collection_books(
        session, collection_id, book_ids
    )
