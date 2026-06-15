"""Search routes (``POST /v1/search``).

Convention: this router uses ``prefix=""`` and individual endpoints
carry their own full ``/v1/...`` paths, matching
:mod:`sentido.catalog.routes`. The admin router is the only exception
— see :mod:`sentido.admin.routes`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.generation.clients import OpenAIClient
from sentido.search import service as search_service
from sentido.search.schemas import SearchRequest, SearchResponse
from sentido.shared.db import get_session

router = APIRouter(tags=["search"])


@router.post(
    "/v1/search",
    response_model=SearchResponse,
    status_code=200,
)
async def search(
    body: SearchRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SearchResponse:
    """Semantic search across the published catalog (plan §5.1).

    Embeds the query and ranks published books by pgvector cosine
    similarity. Each result carries a per-(query, book) resonance line
    generated lazily on first ask and cached in ``resonance_cache``.

    Status codes:
        * 200 — results (possibly empty).
        * 422 — request body validation failure (Pydantic).
        * 503 — OpenAI embedding upstream is down.
    """
    openai_client = OpenAIClient(request.app.state.openai_client)
    return await search_service.semantic_search(
        session=session,
        openai_client=openai_client,
        q=body.q,
        limit=body.limit,
    )
