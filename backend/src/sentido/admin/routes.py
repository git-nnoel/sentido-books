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

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.admin import service as admin_service
from sentido.admin.schemas import (
    AdminBookListResponse,
    AdminBookResponse,
    BookEditRequest,
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
