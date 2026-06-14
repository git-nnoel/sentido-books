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

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.admin import service as admin_service
from sentido.admin.schemas import AdminBookResponse, IngestRequest
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
