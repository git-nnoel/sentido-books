"""Integration tests for ``catalog.service`` write + read paths.

Skill R15 (Mode B): the test DB is real (``sentido_test`` on the dev
Postgres container — fixtures live in ``backend/conftest.py``); no
external services are involved here since catalog has no HTTP/LLM
clients of its own.

Covers B5 surface area:
    * :func:`update_book` — partial writes + the publish gate.
    * :func:`get_published_book_by_slug` — 404 / published filtering.
    * :func:`find_related_books` — pgvector ranking + filtering.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.catalog import service as catalog_service
from sentido.catalog.models import AuthorORM, BookORM
from sentido.shared.errors import ApiError

# 1536-dim vectors used to seed deterministic embeddings.
_VEC_A: list[float] = [1.0] + [0.0] * 1535
_VEC_B: list[float] = [0.0, 1.0] + [0.0] * 1534


@pytest_asyncio.fixture
async def author(test_session: AsyncSession) -> AuthorORM:
    a = AuthorORM(slug="albert-camus", name="Albert Camus")
    test_session.add(a)
    await test_session.commit()
    return a


async def _make_book(
    session: AsyncSession,
    *,
    author_id: uuid.UUID,
    slug: str,
    title: str,
    published: bool = False,
    embedding_status: str = "pending",
    profile_status: str = "pending",
    embedding: list[float] | None = None,
    synopsis: str | None = None,
    emotional_profile: dict | None = None,
) -> BookORM:
    book = BookORM(
        slug=slug,
        title=title,
        author_id=author_id,
        year_published=1942,
        synopsis=synopsis,
        emotional_profile=emotional_profile,
        atmosphere_tags=[],
        narrative_pace=None,
        embedding=embedding,
        embedding_status=embedding_status,
        profile_status=profile_status,
        published=published,
    )
    session.add(book)
    await session.commit()
    return book


# ---------------------------------------------------------------------------
# update_book — partial updates + publish gate.
# ---------------------------------------------------------------------------


class TestUpdateBookPartial:
    async def test_patches_only_listed_fields(
        self, test_session: AsyncSession, author: AuthorORM
    ) -> None:
        book = await _make_book(
            test_session,
            author_id=author.id,
            slug="o-estrangeiro",
            title="O Estrangeiro",
            synopsis="old synopsis",
        )
        old_updated = book.updated_at

        updated = await catalog_service.update_book(
            test_session, book.id, {"synopsis": "new synopsis"}
        )

        assert updated.synopsis == "new synopsis"
        assert updated.title == "O Estrangeiro"  # untouched
        assert updated.published is False  # untouched
        # ``updated_at`` is stamped by the service.
        assert updated.updated_at >= old_updated


class TestUpdateBookPublishGate:
    async def test_blocks_when_embedding_pending(
        self, test_session: AsyncSession, author: AuthorORM
    ) -> None:
        book = await _make_book(
            test_session,
            author_id=author.id,
            slug="o-estrangeiro",
            title="O Estrangeiro",
            embedding_status="pending",
            profile_status="approved",
        )
        with pytest.raises(ApiError) as exc:
            await catalog_service.update_book(
                test_session, book.id, {"published": True}
            )
        assert exc.value.status_code == 422
        assert "cannot publish" in exc.value.detail

    async def test_blocks_when_profile_not_approved(
        self, test_session: AsyncSession, author: AuthorORM
    ) -> None:
        book = await _make_book(
            test_session,
            author_id=author.id,
            slug="o-estrangeiro",
            title="O Estrangeiro",
            embedding_status="done",
            profile_status="pending",
            embedding=_VEC_A,
        )
        with pytest.raises(ApiError) as exc:
            await catalog_service.update_book(
                test_session, book.id, {"published": True}
            )
        assert exc.value.status_code == 422

    async def test_succeeds_when_both_gates_pass(
        self, test_session: AsyncSession, author: AuthorORM
    ) -> None:
        book = await _make_book(
            test_session,
            author_id=author.id,
            slug="o-estrangeiro",
            title="O Estrangeiro",
            embedding_status="done",
            profile_status="approved",
            embedding=_VEC_A,
        )
        updated = await catalog_service.update_book(
            test_session, book.id, {"published": True}
        )
        assert updated.published is True

    async def test_publish_in_single_patch_with_approve(
        self, test_session: AsyncSession, author: AuthorORM
    ) -> None:
        """Approving + publishing in one PATCH must succeed when the
        embedding is already present (gate runs on post-patch state)."""
        book = await _make_book(
            test_session,
            author_id=author.id,
            slug="o-estrangeiro",
            title="O Estrangeiro",
            embedding_status="done",
            profile_status="pending",
            embedding=_VEC_A,
        )
        updated = await catalog_service.update_book(
            test_session,
            book.id,
            {"profile_status": "approved", "published": True},
        )
        assert updated.published is True
        assert updated.profile_status == "approved"


# ---------------------------------------------------------------------------
# get_published_book_by_slug.
# ---------------------------------------------------------------------------


class TestGetPublishedBookBySlug:
    async def test_404_when_unpublished(
        self, test_session: AsyncSession, author: AuthorORM
    ) -> None:
        await _make_book(
            test_session,
            author_id=author.id,
            slug="o-estrangeiro",
            title="O Estrangeiro",
            published=False,
        )
        with pytest.raises(ApiError) as exc:
            await catalog_service.get_published_book_by_slug(
                test_session, "o-estrangeiro"
            )
        assert exc.value.status_code == 404

    async def test_404_when_unknown(self, test_session: AsyncSession) -> None:
        with pytest.raises(ApiError) as exc:
            await catalog_service.get_published_book_by_slug(
                test_session, "does-not-exist"
            )
        assert exc.value.status_code == 404

    async def test_returns_with_relations(
        self, test_session: AsyncSession, author: AuthorORM
    ) -> None:
        await _make_book(
            test_session,
            author_id=author.id,
            slug="o-estrangeiro",
            title="O Estrangeiro",
            published=True,
            embedding_status="done",
            profile_status="approved",
            embedding=_VEC_A,
        )
        book = await catalog_service.get_published_book_by_slug(
            test_session, "o-estrangeiro"
        )
        assert book.slug == "o-estrangeiro"
        # ``author`` is eager-loaded.
        assert book.author.slug == "albert-camus"
        # ``editions`` is eager-loaded (empty list in this seed).
        assert list(book.editions) == []


# ---------------------------------------------------------------------------
# find_related_books.
# ---------------------------------------------------------------------------


class TestFindRelatedBooks:
    async def test_excludes_self(
        self, test_session: AsyncSession, author: AuthorORM
    ) -> None:
        target = await _make_book(
            test_session,
            author_id=author.id,
            slug="target",
            title="Target",
            published=True,
            embedding_status="done",
            embedding=_VEC_A,
        )
        await _make_book(
            test_session,
            author_id=author.id,
            slug="other",
            title="Other",
            published=True,
            embedding_status="done",
            embedding=_VEC_B,
        )
        related = await catalog_service.find_related_books(test_session, target)
        slugs = [b.slug for b in related]
        assert "target" not in slugs
        assert "other" in slugs

    async def test_excludes_unpublished(
        self, test_session: AsyncSession, author: AuthorORM
    ) -> None:
        target = await _make_book(
            test_session,
            author_id=author.id,
            slug="target",
            title="Target",
            published=True,
            embedding_status="done",
            embedding=_VEC_A,
        )
        # Unpublished neighbour should not appear.
        await _make_book(
            test_session,
            author_id=author.id,
            slug="hidden",
            title="Hidden",
            published=False,
            embedding_status="done",
            embedding=_VEC_B,
        )
        related = await catalog_service.find_related_books(test_session, target)
        assert [b.slug for b in related] == []

    async def test_returns_empty_when_no_embedding(
        self, test_session: AsyncSession, author: AuthorORM
    ) -> None:
        target = await _make_book(
            test_session,
            author_id=author.id,
            slug="target",
            title="Target",
            published=True,
            embedding_status="pending",
            embedding=None,
        )
        await _make_book(
            test_session,
            author_id=author.id,
            slug="other",
            title="Other",
            published=True,
            embedding_status="done",
            embedding=_VEC_B,
        )
        related = await catalog_service.find_related_books(test_session, target)
        assert related == []
