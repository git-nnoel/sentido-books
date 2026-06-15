"""Search service — orchestrates query embedding, pgvector search, resonance-line cache.

Plan §3.3 (M3 / M5 / M8): the only OpenAI seam this module uses to
generate resonance lines is :func:`sentido.generation.service.generate_resonance_line`
— spoke→spoke imports of ``routes.py``/``logic.py`` are forbidden.
The query-embedding call uses the same :class:`OpenAIClient` wrapper
through its ``embed`` method.

Workflow (plan §5.1 + §6):
    1. Normalize the query (whitespace collapse).
    2. Embed the normalized query (OpenAI text-embedding-3-small).
       Upstream failures surface as HTTP 503 — search is the only
       endpoint where embedding outage is recoverable; in book
       generation the same failure is a 502.
    3. Run the pgvector cosine-distance query over published books
       with an embedding.
    4. For each result, look up the resonance line in
       ``resonance_cache`` (composite PK ``query_hash, book_id``); on
       miss, call ``generation.service.generate_resonance_line`` and
       insert the result.
    5. Assemble :class:`SearchResponse` with cosine similarity (1 -
       distance).

Cache key parity (plan §6): the same
:func:`sentido.search.logic.cache_key` helper is used for both the
SELECT and the INSERT side so the two halves cannot drift apart.
"""

from __future__ import annotations

from openai import APIError, OpenAIError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentido.catalog.models import BookORM
from sentido.generation import service as generation_service
from sentido.generation.clients import OpenAIClient
from sentido.search.logic import (
    cache_key,
    cosine_similarity_from_distance,
    normalize_query,
)
from sentido.search.models import ResonanceCacheORM
from sentido.search.schemas import SearchResponse, SearchResultItem
from sentido.shared.errors import ApiError


async def semantic_search(
    *,
    session: AsyncSession,
    openai_client: OpenAIClient,
    q: str,
    limit: int,
) -> SearchResponse:
    """Run a semantic-search query end-to-end.

    See module docstring for the workflow. Returns an empty
    ``results`` list when no books match (e.g., catalog is empty or
    no published row has an embedding) — that's not an error.

    Errors:
        * 503 — OpenAI embedding call failed (network, rate-limit,
          parse). Per plan §5.1 wording: ``"search temporarily
          unavailable"``.
        * 502 — A resonance-line generation call failed (propagated
          from :func:`generation.service.generate_resonance_line`).
    """
    normalized = normalize_query(q)

    # --- 1) embed the query --------------------------------------------
    # The OpenAI wrapper retries transient errors per plan §7.1; only
    # the *final* failure reaches us here. Any failure here means we
    # cannot rank the catalog — surface as 503, not 502, because the
    # rest of the system is healthy and a retry might recover.
    try:
        query_vector = await openai_client.embed(normalized)
    except (OpenAIError, APIError, ValueError) as exc:
        raise ApiError(503, "search temporarily unavailable") from exc

    # --- 2) pgvector cosine-distance search ----------------------------
    # Plan §4.1 ivfflat index (vector_cosine_ops) backs the ORDER BY.
    # The filter ``embedding_status='done'`` is redundant with the
    # ``IS NOT NULL`` check in practice (generation sets both together)
    # but the plan §5.1 contract names it explicitly — we follow the
    # contract to keep the SQL self-explanatory.
    distance_expr = BookORM.embedding.cosine_distance(query_vector).label("distance")
    stmt = (
        select(BookORM, distance_expr)
        .where(BookORM.published.is_(True))
        .where(BookORM.embedding.is_not(None))
        .where(BookORM.embedding_status == "done")
        .order_by(distance_expr)
        .limit(limit)
        .options(selectinload(BookORM.author))
    )
    rows = (await session.execute(stmt)).all()

    if not rows:
        return SearchResponse(query=normalized, results=[])

    # --- 3) resolve resonance lines (cache read, then write on miss) ---
    results: list[SearchResultItem] = []
    cache_dirty = False
    for book, distance in rows:
        key = cache_key(normalized, book.id)

        cached_line = await session.scalar(
            select(ResonanceCacheORM.line).where(
                ResonanceCacheORM.query_hash == key,
                ResonanceCacheORM.book_id == book.id,
            )
        )

        if cached_line is None:
            generated = await generation_service.generate_resonance_line(
                openai_client=openai_client,
                query=normalized,
                book=book,
            )
            # ``ON CONFLICT DO NOTHING`` tolerates the (rare under solo
            # curator, but cheap to guard) race where two concurrent
            # searches generated the same (query, book) line.
            await session.execute(
                pg_insert(ResonanceCacheORM)
                .values(query_hash=key, book_id=book.id, line=generated)
                .on_conflict_do_nothing(index_elements=["query_hash", "book_id"])
            )
            cache_dirty = True
            line = generated
        else:
            line = cached_line

        results.append(
            SearchResultItem(
                slug=book.slug,
                title=book.title,
                author_name=book.author.name,
                year_published=book.year_published,
                cover_url=book.cover_url,
                resonance_line=line,
                similarity=cosine_similarity_from_distance(float(distance)),
            )
        )

    if cache_dirty:
        await session.commit()

    return SearchResponse(query=normalized, results=results)
