"""Search DTOs — public ``POST /v1/search`` request/response shapes (plan §5.1).

Pydantic v2. ``model_config = ConfigDict(extra="forbid")`` on every
model so an unexpected field in the request body or in a result row
surfaces as a 422 rather than silently being dropped.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SearchRequest(BaseModel):
    """Public search request body (plan §5.1).

    ``q`` must be 1–500 chars; ``limit`` is bounded to 1–50 with a
    default of 12 to match the plan's contract.
    """

    model_config = ConfigDict(extra="forbid")

    q: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=12, ge=1, le=50)


class SearchResultItem(BaseModel):
    """One book result inside a :class:`SearchResponse` (plan §5.1).

    ``similarity`` is the cosine similarity (1 = same, -1 = opposite),
    computed from pgvector's cosine *distance* by
    :func:`sentido.search.logic.cosine_similarity_from_distance`.
    """

    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    author_name: str
    year_published: int | None = None
    cover_url: str | None = None
    resonance_line: str
    similarity: float


class SearchResponse(BaseModel):
    """Public search response envelope (plan §5.1).

    ``query`` is the **normalized** query (whitespace collapsed) — the
    same value used as the resonance-cache key — so the frontend can
    echo what the server actually searched for.
    """

    model_config = ConfigDict(extra="forbid")

    query: str
    results: list[SearchResultItem]
