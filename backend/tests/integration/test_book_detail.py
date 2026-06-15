"""Integration tests for ``GET /v1/books/{slug}`` (B5).

Public endpoint, no auth. The test pins the app's sessionmaker to the
integration test engine; no external HTTP / LLM clients are used by
this endpoint.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from sentido.catalog.models import AuthorORM, BookORM
from sentido.main import create_app

_VEC: list[float] = [0.01] * 1536


@pytest.fixture
def client(test_engine: AsyncEngine) -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as tc:
        app.state.sessionmaker = async_sessionmaker(
            test_engine, expire_on_commit=False
        )
        yield tc


async def _seed_book(
    test_session,
    *,
    slug: str,
    title: str,
    published: bool,
    with_embedding: bool = True,
) -> BookORM:
    author = AuthorORM(slug="albert-camus", name="Albert Camus")
    test_session.add(author)
    await test_session.flush()
    book = BookORM(
        slug=slug,
        title=title,
        author_id=author.id,
        year_published=1942,
        synopsis="seed synopsis",
        emotional_profile={
            "anguish": 6.0,
            "melancholy": 4.0,
            "hope": 1.0,
            "violence": 5.0,
            "tenderness": 1.0,
            "strangeness": 8.5,
        },
        atmosphere_tags=["apatia"],
        narrative_pace="progressive",
        embedding=_VEC if with_embedding else None,
        embedding_status="done" if with_embedding else "pending",
        profile_status="approved",
        published=published,
    )
    test_session.add(book)
    await test_session.commit()
    return book


class TestGetBookBySlug:
    async def test_published_returns_full_payload(
        self,
        client: TestClient,
        test_session,
    ) -> None:
        await _seed_book(
            test_session, slug="o-estrangeiro", title="O Estrangeiro", published=True
        )
        response = client.get("/v1/books/o-estrangeiro")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["slug"] == "o-estrangeiro"
        assert body["title"] == "O Estrangeiro"
        assert body["author"]["slug"] == "albert-camus"
        assert body["synopsis"] == "seed synopsis"
        assert body["atmosphere_tags"] == ["apatia"]
        assert body["narrative_pace"] == "progressive"
        assert body["emotional_profile"]["anguish"] == 6.0
        # No admin-only fields leak past the public contract.
        for forbidden in ("id", "embedding_status", "profile_status", "published"):
            assert forbidden not in body
        # No related books seeded.
        assert body["related_books"] == []

    async def test_unpublished_returns_404(
        self,
        client: TestClient,
        test_session,
    ) -> None:
        await _seed_book(
            test_session, slug="not-yet", title="Not Yet", published=False
        )
        response = client.get("/v1/books/not-yet")
        assert response.status_code == 404
        assert response.json() == {"detail": "book not found"}

    async def test_unknown_returns_404(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/v1/books/does-not-exist")
        assert response.status_code == 404
        assert response.json() == {"detail": "book not found"}
