"""Integration tests for the public collection endpoints (B7 / plan §14.1).

Covers:
    * ``GET /v1/collections`` — list published collections, empty (200),
      pagination total.
    * ``GET /v1/collections/{slug}`` — happy path (published books only,
      ordered by position) + 404 when unpublished or missing.

Public endpoints, no auth. The route path is route → catalog service →
Postgres; no external HTTP / LLM clients are involved, so we only pin
the app's sessionmaker to the integration test engine (mirrors
``test_book_detail.py``).
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sentido.catalog.models import (
    AuthorORM,
    BookORM,
    CollectionBookORM,
    CollectionORM,
)
from sentido.main import create_app
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


@pytest.fixture
def client(test_engine: AsyncEngine) -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as tc:
        app.state.sessionmaker = async_sessionmaker(
            test_engine, expire_on_commit=False
        )
        yield tc


async def _seed_author(test_session) -> AuthorORM:
    author = AuthorORM(slug="albert-camus", name="Albert Camus")
    test_session.add(author)
    await test_session.flush()
    return author


async def _make_book(
    test_session,
    author: AuthorORM,
    *,
    slug: str,
    title: str,
    published: bool,
) -> BookORM:
    book = BookORM(
        slug=slug,
        title=title,
        author_id=author.id,
        year_published=1942,
        published=published,
        embedding_status="done" if published else "pending",
        profile_status="approved" if published else "pending",
    )
    test_session.add(book)
    await test_session.flush()
    return book


class TestListCollections:
    async def test_lists_only_published_ordered_by_updated_desc(
        self,
        client: TestClient,
        test_session,
    ) -> None:
        base = dt.datetime(2026, 6, 1, 12, 0, tzinfo=dt.UTC)
        test_session.add_all(
            [
                CollectionORM(
                    slug="col-velha",
                    title="Coleção Velha",
                    description="a",
                    published=True,
                    updated_at=base,
                ),
                CollectionORM(
                    slug="col-nova",
                    title="Coleção Nova",
                    description="b",
                    published=True,
                    updated_at=base + dt.timedelta(hours=1),
                ),
                CollectionORM(
                    slug="col-rascunho",
                    title="Rascunho",
                    description=None,
                    published=False,
                    updated_at=base + dt.timedelta(hours=2),
                ),
            ]
        )
        await test_session.commit()

        response = client.get("/v1/collections")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 2
        # updated_at DESC — the newer published collection comes first;
        # the draft never appears.
        assert [c["slug"] for c in body["collections"]] == ["col-nova", "col-velha"]
        assert body["collections"][0]["description"] == "b"

    async def test_empty_is_200_not_404(
        self,
        client: TestClient,
        test_session,
    ) -> None:
        response = client.get("/v1/collections")
        assert response.status_code == 200, response.text
        assert response.json() == {"collections": [], "total": 0}

    async def test_pagination_reports_unpaginated_total(
        self,
        client: TestClient,
        test_session,
    ) -> None:
        base = dt.datetime(2026, 6, 1, 12, 0, tzinfo=dt.UTC)
        for i in range(3):
            test_session.add(
                CollectionORM(
                    slug=f"col-{i}",
                    title=f"Col {i}",
                    published=True,
                    updated_at=base + dt.timedelta(hours=i),
                )
            )
        await test_session.commit()

        response = client.get("/v1/collections", params={"limit": 1})
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 3
        assert len(body["collections"]) == 1
        assert body["collections"][0]["slug"] == "col-2"


class TestGetCollectionBySlug:
    async def test_published_returns_published_books_ordered(
        self,
        client: TestClient,
        test_session,
    ) -> None:
        author = await _seed_author(test_session)
        collection = CollectionORM(
            slug="livros-que-ficam",
            title="Livros que ficam no corpo",
            description="…",
            published=True,
        )
        test_session.add(collection)
        await test_session.flush()

        b0 = await _make_book(
            test_session, author, slug="livro-0", title="Livro 0", published=True
        )
        b1 = await _make_book(
            test_session, author, slug="livro-1", title="Livro 1", published=True
        )
        # Unpublished book — must be filtered out of the public payload.
        b_draft = await _make_book(
            test_session, author, slug="livro-draft", title="Draft", published=False
        )

        # Insert links out of position order to prove the ORDER BY works.
        test_session.add_all(
            [
                CollectionBookORM(
                    collection_id=collection.id, book_id=b1.id, position=1
                ),
                CollectionBookORM(
                    collection_id=collection.id, book_id=b0.id, position=0
                ),
                CollectionBookORM(
                    collection_id=collection.id, book_id=b_draft.id, position=2
                ),
            ]
        )
        await test_session.commit()

        response = client.get("/v1/collections/livros-que-ficam")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["slug"] == "livros-que-ficam"
        assert body["title"] == "Livros que ficam no corpo"
        # position ASC; draft excluded.
        assert [b["slug"] for b in body["books"]] == ["livro-0", "livro-1"]
        assert body["books"][0]["author_name"] == "Albert Camus"

    async def test_unpublished_collection_returns_404(
        self,
        client: TestClient,
        test_session,
    ) -> None:
        test_session.add(
            CollectionORM(slug="oculta", title="Oculta", published=False)
        )
        await test_session.commit()

        response = client.get("/v1/collections/oculta")
        assert response.status_code == 404
        assert response.json() == {"detail": "collection not found"}

    async def test_missing_collection_returns_404(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/v1/collections/nope")
        assert response.status_code == 404
        assert response.json() == {"detail": "collection not found"}
