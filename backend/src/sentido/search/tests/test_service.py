"""Integration tests for ``search.service.semantic_search``.

Skill R15 (Mode B): the test DB is real (``sentido_test``), OpenAI is
stubbed at the wrapper boundary. We use a single fake that returns:
    * canned embeddings (we control which book ranks first by aligning
      the query vector with a known seed vector),
    * canned resonance lines (so cache hits/misses can be asserted by
      counting chat calls).

The pgvector cosine-distance ordering is the production code path —
the fake only stands in for the LLM calls.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
import pytest_asyncio
from openai import OpenAIError, RateLimitError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.catalog.models import AuthorORM, BookORM
from sentido.search import service as search_service
from sentido.search.models import ResonanceCacheORM
from sentido.shared.errors import ApiError

# Three deterministic 1536-dim vectors. Each book gets one; the query
# embedding is aligned with vector A so the "alpha" book ranks first.

_DIM = 1536


def _vec(i: int) -> list[float]:
    v = [0.0] * _DIM
    v[i] = 1.0
    return v


_VEC_A = _vec(0)
_VEC_B = _vec(1)
_VEC_C = _vec(2)


# ---------------------------------------------------------------------------
# Fake OpenAI client.
# ---------------------------------------------------------------------------


class _SearchFakeClient:
    """Stand-in for :class:`OpenAIClient` used in semantic_search tests.

    * ``embed`` returns ``query_vector`` by default (aligned with the
      "alpha" book so it ranks first).
    * ``chat`` returns a per-book canned resonance line keyed by title,
      and tracks the number of chat calls so cache-hit tests can
      assert "no second LLM call".
    * ``raise_on_embed`` short-circuits to ``RateLimitError`` to test
      the 503 path.
    """

    def __init__(
        self,
        *,
        query_vector: list[float] | None = None,
        raise_on_embed: Exception | None = None,
        resonance_line: str = "uma frase que ressoa.",
    ) -> None:
        self._query_vector = query_vector if query_vector is not None else list(_VEC_A)
        self._raise_on_embed = raise_on_embed
        self._resonance_line = resonance_line
        self.chat_calls: list[dict[str, Any]] = []
        self.embed_calls: list[str] = []

    async def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        if self._raise_on_embed is not None:
            raise self._raise_on_embed
        return list(self._query_vector)

    async def chat(self, **kwargs: Any) -> str:
        self.chat_calls.append(kwargs)
        return self._resonance_line


def _rate_limit_error() -> RateLimitError:
    response = httpx.Response(429, request=httpx.Request("POST", "https://stub"))
    return RateLimitError("rate limited", response=response, body=None)


# ---------------------------------------------------------------------------
# Seeding helpers.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def author(test_session: AsyncSession) -> AuthorORM:
    a = AuthorORM(slug="albert-camus", name="Albert Camus")
    test_session.add(a)
    await test_session.commit()
    return a


async def _make_book(
    session: AsyncSession,
    *,
    author_id: Any,
    slug: str,
    title: str,
    embedding: list[float] | None,
    published: bool = True,
    embedding_status: str = "done",
    profile_status: str = "approved",
) -> BookORM:
    book = BookORM(
        slug=slug,
        title=title,
        author_id=author_id,
        year_published=1942,
        synopsis="seed synopsis",
        atmosphere_tags=[],
        narrative_pace="progressive",
        embedding=embedding,
        embedding_status=embedding_status,
        profile_status=profile_status,
        published=published,
    )
    session.add(book)
    await session.commit()
    return book


@pytest_asyncio.fixture
async def seed_three(
    test_session: AsyncSession, author: AuthorORM
) -> tuple[BookORM, BookORM, BookORM]:
    """Three published books with embeddings A, B, C respectively."""
    a = await _make_book(
        test_session,
        author_id=author.id,
        slug="alpha",
        title="Alpha",
        embedding=_VEC_A,
    )
    b = await _make_book(
        test_session,
        author_id=author.id,
        slug="bravo",
        title="Bravo",
        embedding=_VEC_B,
    )
    c = await _make_book(
        test_session,
        author_id=author.id,
        slug="charlie",
        title="Charlie",
        embedding=_VEC_C,
    )
    return a, b, c


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


class TestSemanticSearchRanking:
    async def test_returns_ranked_results(
        self,
        test_session: AsyncSession,
        seed_three: tuple[BookORM, BookORM, BookORM],
    ) -> None:
        fake = _SearchFakeClient(query_vector=_VEC_A)
        response = await search_service.semantic_search(
            session=test_session,
            openai_client=fake,  # type: ignore[arg-type]
            q="anything",
            limit=12,
        )
        assert response.query == "anything"
        assert [r.slug for r in response.results][0] == "alpha"
        # All three rank.
        assert {r.slug for r in response.results} == {"alpha", "bravo", "charlie"}
        # similarity for "alpha" should be ~1.0 (cosine distance ~0).
        alpha = next(r for r in response.results if r.slug == "alpha")
        assert alpha.similarity == pytest.approx(1.0, abs=1e-4)


class TestSemanticSearchFilters:
    async def test_excludes_unpublished(
        self,
        test_session: AsyncSession,
        author: AuthorORM,
    ) -> None:
        await _make_book(
            test_session,
            author_id=author.id,
            slug="published",
            title="Published",
            embedding=_VEC_A,
        )
        await _make_book(
            test_session,
            author_id=author.id,
            slug="hidden",
            title="Hidden",
            embedding=_VEC_B,
            published=False,
        )
        fake = _SearchFakeClient()
        response = await search_service.semantic_search(
            session=test_session,
            openai_client=fake,  # type: ignore[arg-type]
            q="x",
            limit=12,
        )
        assert {r.slug for r in response.results} == {"published"}

    async def test_excludes_pending_embedding(
        self,
        test_session: AsyncSession,
        author: AuthorORM,
    ) -> None:
        await _make_book(
            test_session,
            author_id=author.id,
            slug="ready",
            title="Ready",
            embedding=_VEC_A,
        )
        await _make_book(
            test_session,
            author_id=author.id,
            slug="pending",
            title="Pending",
            embedding=_VEC_B,
            embedding_status="pending",
        )
        fake = _SearchFakeClient()
        response = await search_service.semantic_search(
            session=test_session,
            openai_client=fake,  # type: ignore[arg-type]
            q="x",
            limit=12,
        )
        assert {r.slug for r in response.results} == {"ready"}


class TestSemanticSearchCache:
    async def test_caches_resonance_lines(
        self,
        test_session: AsyncSession,
        seed_three: tuple[BookORM, BookORM, BookORM],
    ) -> None:
        fake = _SearchFakeClient()
        response_a = await search_service.semantic_search(
            session=test_session,
            openai_client=fake,  # type: ignore[arg-type]
            q="solidão que não dói",
            limit=12,
        )
        # First call: 3 chat invocations (one per result).
        assert len(fake.chat_calls) == 3
        assert all(r.resonance_line for r in response_a.results)

        # Cache rows persisted.
        cached = (
            await test_session.scalars(select(ResonanceCacheORM))
        ).all()
        assert len(cached) == 3

        # Second call, same query: zero new chat invocations.
        response_b = await search_service.semantic_search(
            session=test_session,
            openai_client=fake,  # type: ignore[arg-type]
            q="solidão que não dói",
            limit=12,
        )
        assert len(fake.chat_calls) == 3  # unchanged
        # Lines are the cached ones.
        assert {r.resonance_line for r in response_b.results} == {
            "uma frase que ressoa."
        }


class TestSemanticSearchUpstreamFailure:
    async def test_503_when_openai_embedding_fails(
        self,
        test_session: AsyncSession,
        seed_three: tuple[BookORM, BookORM, BookORM],
    ) -> None:
        fake = _SearchFakeClient(raise_on_embed=_rate_limit_error())
        with pytest.raises(ApiError) as exc:
            await search_service.semantic_search(
                session=test_session,
                openai_client=fake,  # type: ignore[arg-type]
                q="x",
                limit=12,
            )
        assert exc.value.status_code == 503
        assert exc.value.detail == "search temporarily unavailable"

    async def test_503_on_generic_openai_error(
        self,
        test_session: AsyncSession,
        seed_three: tuple[BookORM, BookORM, BookORM],
    ) -> None:
        fake = _SearchFakeClient(raise_on_embed=OpenAIError("down"))
        with pytest.raises(ApiError) as exc:
            await search_service.semantic_search(
                session=test_session,
                openai_client=fake,  # type: ignore[arg-type]
                q="x",
                limit=12,
            )
        assert exc.value.status_code == 503


class TestSemanticSearchEmptyCatalog:
    async def test_returns_empty_results(self, test_session: AsyncSession) -> None:
        fake = _SearchFakeClient()
        response = await search_service.semantic_search(
            session=test_session,
            openai_client=fake,  # type: ignore[arg-type]
            q="anything",
            limit=12,
        )
        assert response.results == []
        # Embedding was still called (we don't optimize the empty-catalog
        # path with a pre-count) — that's an acceptable trade for v1.
        assert len(fake.embed_calls) == 1
