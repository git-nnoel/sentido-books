"""Admin routes (``/v1/admin/...``).

The router carries ``prefix="/v1/admin"`` and ``dependencies=[Depends(
require_admin)]`` so EVERY admin endpoint added in later tasks (B4+)
inherits bearer-token auth by default. Future endpoints should NOT
re-declare ``require_admin`` per route — that's the whole point of
attaching it here.

Public catalog/search routers do not share this prefix; they each carry
their own full ``/v1/...`` paths. See :mod:`sentido.catalog.routes` for
the convention.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.admin import service as admin_service
from sentido.admin.schemas import (
    AdminBookListResponse,
    AdminBookResponse,
    AdminCollection,
    AdminCollectionBook,
    AdminCollectionListResponse,
    BookEditRequest,
    CollectionBooksReplaceRequest,
    CollectionCreateRequest,
    CollectionEditRequest,
    IngestRequest,
)
from sentido.generation.clients import OpenAIClient
from sentido.generation.schemas import GenerationRequest
from sentido.shared.auth import require_admin
from sentido.shared.db import get_session

router = APIRouter(
    prefix="/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.get(
    "/books",
    response_model=AdminBookListResponse,
    status_code=200,
)
async def list_books(
    session: Annotated[AsyncSession, Depends(get_session)],
    status: Annotated[
        Literal["pending_generation", "pending_approval", "published", "all"],
        Query(description="Status filter for the admin queue view."),
    ] = "pending_generation",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminBookListResponse:
    """List books with admin filters (plan §5.2).

    Backs the admin panel queue view. The default ``status`` is
    ``pending_generation`` — the curator's most common landing query —
    and the page is ordered by ``updated_at`` DESC so the most recently
    touched rows surface first. ``total`` carries the unpaginated count
    of matches so the panel can render its pagination controls without
    a second round-trip.

    Auth: gated by the router-level ``Depends(require_admin)``.
    """
    books, total = await admin_service.list_books(
        session,
        status_filter=status,
        limit=limit,
        offset=offset,
    )
    return AdminBookListResponse(
        books=[AdminBookResponse.from_orm(book) for book in books],
        total=total,
    )


@router.post(
    "/books/ingest",
    response_model=AdminBookResponse,
    status_code=201,
)
async def ingest_book(
    body: IngestRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminBookResponse:
    """Ingest a book from Open Library by ISBN (plan §5.2).

    The shared httpx client lives on ``app.state.httpx_client`` (built
    in the FastAPI lifespan, plan §3 / skill R6). The route hands it
    plus the per-request session to the admin service, then converts
    the persisted ORM into the contract DTO.

    Status codes (raised inside the service via ``ApiError``):
        * 400 — invalid ISBN format (raised as ``ValueError``)
        * 404 — ISBN unknown to Open Library / metadata incomplete
        * 409 — duplicate ISBN
        * 502 — Open Library unreachable
    """
    http_client = request.app.state.httpx_client
    book = await admin_service.ingest_book(session, http_client, body.isbn)
    return AdminBookResponse.from_orm(book)


@router.post(
    "/books/{book_id}/generate",
    response_model=AdminBookResponse,
    status_code=200,
)
async def generate_book_artifacts(
    book_id: uuid.UUID,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    body: GenerationRequest | None = None,
) -> AdminBookResponse:
    """Generate synopsis + emotional profile + embedding (plan §5.2).

    The body is optional — an empty request (``{}`` or no body at all)
    defaults to ``regenerate=False``. The shared OpenAI client lives on
    ``app.state.openai_client`` (built in the lifespan, skill R6); the
    route hands a thin wrapper of it to the admin service.

    Status codes (raised inside the service via ``ApiError``):
        * 404 — book id not found
        * 409 — book already has artifacts and ``regenerate`` is false
        * 502 — OpenAI upstream failure (network, parse, or auth)
    """
    payload = body or GenerationRequest()
    openai_client = OpenAIClient(request.app.state.openai_client)
    book = await admin_service.generate_book_artifacts(
        session=session,
        openai_client=openai_client,
        book_id=book_id,
        regenerate=payload.regenerate,
    )
    return AdminBookResponse.from_orm(book)


@router.put(
    "/books/{book_id}",
    response_model=AdminBookResponse,
    status_code=200,
)
async def edit_book(
    book_id: uuid.UUID,
    body: BookEditRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminBookResponse:
    """Partial update of a book (plan §5.2).

    Body shape: any subset of the curator-editable fields. Unknown
    fields → 422 (Pydantic's ``extra="forbid"``). Empty body → 400
    ("no fields to update"). Setting ``published=true`` requires the
    post-patch state to satisfy ``profile_status=approved`` AND
    ``embedding_status=done`` — otherwise the service raises 422.

    ``model_dump(exclude_unset=True)`` is what crosses the route →
    service boundary so "field missing" stays distinct from "field
    explicitly set to None" (the latter is a valid clear operation).
    """
    patch_dict = body.model_dump(exclude_unset=True)
    book = await admin_service.update_book(session, book_id, patch_dict)
    return AdminBookResponse.from_orm(book)


@router.post(
    "/books/{book_id}/publish",
    response_model=AdminBookResponse,
    status_code=200,
)
async def publish_book(
    book_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminBookResponse:
    """Approve + publish a book in one call (plan §5.2).

    Equivalent to ``PUT /v1/admin/books/{id}`` with body
    ``{"profile_status": "approved", "published": true}``. The publish
    gate inside ``catalog.service.update_book`` returns 422 if the
    embedding is still pending — the curator must regenerate before
    publishing in that case.
    """
    book = await admin_service.publish_book(session, book_id)
    return AdminBookResponse.from_orm(book)


# ---------------------------------------------------------------------------
# Collections — admin CRUD (plan §14.2)
# ---------------------------------------------------------------------------


def _collection_to_admin(collection: object) -> AdminCollection:
    """Build the ``AdminCollection`` DTO from a hydrated CollectionORM.

    Requires that ``collection.book_links`` (with each link's
    ``book.author``) is eager-loaded — the catalog service does this for
    every admin collection op. Book entries are ordered by ``position``
    here in the route so the service can return links in whatever order
    the query yields. Includes ALL books regardless of publish state
    (D10); each entry carries its ``published`` flag so the curator
    knows what readers will see.
    """
    links = sorted(
        collection.book_links,  # type: ignore[attr-defined]
        key=lambda link: link.position,
    )
    books = [
        AdminCollectionBook(
            id=link.book.id,
            slug=link.book.slug,
            title=link.book.title,
            author_name=link.book.author.name,
            position=link.position,
            published=link.book.published,
        )
        for link in links
    ]
    return AdminCollection(
        id=collection.id,  # type: ignore[attr-defined]
        slug=collection.slug,  # type: ignore[attr-defined]
        title=collection.title,  # type: ignore[attr-defined]
        description=collection.description,  # type: ignore[attr-defined]
        published=collection.published,  # type: ignore[attr-defined]
        created_at=collection.created_at,  # type: ignore[attr-defined]
        updated_at=collection.updated_at,  # type: ignore[attr-defined]
        books=books,
    )


@router.post(
    "/collections",
    response_model=AdminCollection,
    status_code=201,
)
async def create_collection(
    body: CollectionCreateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminCollection:
    """Create an editorial collection (plan §14.2).

    The slug is auto-derived from ``title`` server-side. A new
    collection starts ``published=false`` with no books — the curator
    composes it via ``PUT /collections/{id}/books`` then publishes via
    ``PUT /collections/{id}``.

    Auth: gated by the router-level ``Depends(require_admin)``.
    """
    collection = await admin_service.create_collection(
        session, title=body.title, description=body.description
    )
    return _collection_to_admin(collection)


@router.get(
    "/collections",
    response_model=AdminCollectionListResponse,
    status_code=200,
)
async def list_collections(
    session: Annotated[AsyncSession, Depends(get_session)],
    status: Annotated[
        Literal["published", "draft", "all"],
        Query(description="Status filter for the admin collection list."),
    ] = "all",
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AdminCollectionListResponse:
    """List collections with a status filter (plan §14.2).

    ``status`` defaults to ``all``. Ordered by ``updated_at DESC``.
    ``total`` is the unpaginated count of matches. Each collection
    carries its full book list (incl. unpublished — D10).
    """
    collections, total = await admin_service.list_collections(
        session,
        status_filter=status,
        limit=limit,
        offset=offset,
    )
    return AdminCollectionListResponse(
        collections=[_collection_to_admin(c) for c in collections],
        total=total,
    )


@router.get(
    "/collections/{collection_id}",
    response_model=AdminCollection,
    status_code=200,
)
async def get_collection(
    collection_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminCollection:
    """Collection detail for admin (plan §14.2 / D10).

    Returns ALL books in the collection — including unpublished — so the
    curator can see and reorder drafts. 404 if the id is unknown.
    """
    collection = await admin_service.get_collection(session, collection_id)
    return _collection_to_admin(collection)


@router.put(
    "/collections/{collection_id}",
    response_model=AdminCollection,
    status_code=200,
)
async def edit_collection(
    collection_id: uuid.UUID,
    body: CollectionEditRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminCollection:
    """Partial update of a collection (plan §14.2).

    Body: any subset of ``{title, description, published}``. Unknown
    fields → 422 (``extra="forbid"``). Empty body → rejected by the
    schema validator. ``model_dump(exclude_unset=True)`` crosses the
    boundary so "field omitted" stays distinct from "set to None"
    (clearing ``description``). The slug is not re-derived on title edits
    (slugs are stable, D5).
    """
    patch_dict = body.model_dump(exclude_unset=True)
    collection = await admin_service.update_collection(
        session, collection_id, patch_dict
    )
    return _collection_to_admin(collection)


@router.delete(
    "/collections/{collection_id}",
    status_code=204,
)
async def delete_collection(
    collection_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    """Delete a collection (plan §14.2).

    Cascades to ``collection_books`` via the FK constraint. 404 if the
    id is unknown; 204 with no body on success.
    """
    await admin_service.delete_collection(session, collection_id)
    return Response(status_code=204)


@router.put(
    "/collections/{collection_id}/books",
    response_model=AdminCollection,
    status_code=200,
)
async def replace_collection_books(
    collection_id: uuid.UUID,
    body: CollectionBooksReplaceRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AdminCollection:
    """Replace the ordered book list in one transaction (plan §14.2 / D9).

    The curator UI sends the full ordered list on every save; the
    service clears existing links and re-inserts at each id's array
    index. An empty list clears the collection. 422 with the first
    missing id if any ``book_id`` is unknown; 404 if the collection
    itself is unknown.
    """
    collection = await admin_service.replace_collection_books(
        session, collection_id, body.book_ids
    )
    return _collection_to_admin(collection)
