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

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.admin import service as admin_service
from sentido.admin.schemas import AdminBookResponse, IngestRequest
from sentido.generation.clients import OpenAIClient
from sentido.generation.schemas import GenerationRequest
from sentido.shared.auth import require_admin
from sentido.shared.db import get_session

router = APIRouter(
    prefix="/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@router.post(
    "/books/ingest",
    response_model=AdminBookResponse,
    status_code=201,
)
async def ingest_book(
    body: IngestRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
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
    body: GenerationRequest | None = None,
    session: AsyncSession = Depends(get_session),  # noqa: B008 — FastAPI idiom
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
