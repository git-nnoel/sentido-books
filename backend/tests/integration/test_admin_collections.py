"""Integration tests for the admin collection endpoints (B7 / plan §14.2).

Covers: create, update, delete, list (all/published/draft filters), get
by id, replace-books happy path, and the inherited ``require_admin``
gate. The endpoints hit route → admin service → catalog service →
Postgres; no external HTTP / LLM clients are involved, so we only pin
the app's sessionmaker to the integration test engine (mirrors
``test_admin_edit.py``).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sentido.catalog.models import AuthorORM, BookORM
from sentido.main import create_app
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(test_engine: AsyncEngine) -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as tc:
        app.state.sessionmaker = async_sessionmaker(
            test_engine, expire_on_commit=False
        )
        yield tc


async def _seed_books(test_session, count: int = 2) -> list[BookORM]:
    author = AuthorORM(slug="albert-camus", name="Albert Camus")
    test_session.add(author)
    await test_session.flush()
    books: list[BookORM] = []
    for i in range(count):
        book = BookORM(
            slug=f"livro-{i}",
            title=f"Livro {i}",
            author_id=author.id,
            published=(i % 2 == 0),  # alternate published/unpublished
            embedding_status="done",
            profile_status="approved",
        )
        test_session.add(book)
        books.append(book)
    await test_session.commit()
    return books


class TestCreateCollection:
    async def test_create_auto_slugs_from_title(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        response = client.post(
            "/v1/admin/collections",
            json={"title": "Livros que ficam no corpo", "description": "…"},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["slug"] == "livros-que-ficam-no-corpo"
        assert body["title"] == "Livros que ficam no corpo"
        assert body["description"] == "…"
        assert body["published"] is False
        assert body["books"] == []
        assert "id" in body and "created_at" in body and "updated_at" in body

    async def test_create_slug_collision_appends_suffix(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        first = client.post(
            "/v1/admin/collections",
            json={"title": "Repetida"},
            headers=_auth_headers(admin_token),
        )
        second = client.post(
            "/v1/admin/collections",
            json={"title": "Repetida"},
            headers=_auth_headers(admin_token),
        )
        assert first.status_code == 201, first.text
        assert second.status_code == 201, second.text
        assert first.json()["slug"] == "repetida"
        assert second.json()["slug"] == "repetida-2"


class TestUpdateCollection:
    async def test_partial_update(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        created = client.post(
            "/v1/admin/collections",
            json={"title": "Antes", "description": "old"},
            headers=_auth_headers(admin_token),
        ).json()

        response = client.put(
            f"/v1/admin/collections/{created['id']}",
            json={"title": "Depois", "published": True},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["title"] == "Depois"
        assert body["published"] is True
        # Slug is stable across title edits (D5).
        assert body["slug"] == "antes"
        # Untouched field unchanged.
        assert body["description"] == "old"

    async def test_empty_patch_rejected(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        created = client.post(
            "/v1/admin/collections",
            json={"title": "X"},
            headers=_auth_headers(admin_token),
        ).json()
        response = client.put(
            f"/v1/admin/collections/{created['id']}",
            json={},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code in (400, 422), response.text

    async def test_update_unknown_id_404(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        response = client.put(
            "/v1/admin/collections/00000000-0000-0000-0000-000000000000",
            json={"title": "x"},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "collection not found"}


class TestDeleteCollection:
    async def test_delete_returns_204(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        created = client.post(
            "/v1/admin/collections",
            json={"title": "Para Deletar"},
            headers=_auth_headers(admin_token),
        ).json()
        response = client.delete(
            f"/v1/admin/collections/{created['id']}",
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 204, response.text
        assert response.content == b""

        # Confirm it's gone.
        follow = client.get(
            f"/v1/admin/collections/{created['id']}",
            headers=_auth_headers(admin_token),
        )
        assert follow.status_code == 404


class TestListAdminCollections:
    async def _seed_three(self, client: TestClient, admin_token: str) -> None:
        for title in ("Pub", "Draft"):
            client.post(
                "/v1/admin/collections",
                json={"title": title},
                headers=_auth_headers(admin_token),
            )
        # Publish the first.
        listing = client.get(
            "/v1/admin/collections",
            params={"status": "all"},
            headers=_auth_headers(admin_token),
        ).json()
        pub_id = next(c["id"] for c in listing["collections"] if c["title"] == "Pub")
        client.put(
            f"/v1/admin/collections/{pub_id}",
            json={"published": True},
            headers=_auth_headers(admin_token),
        )

    async def test_all_filter(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        await self._seed_three(client, admin_token)
        response = client.get(
            "/v1/admin/collections",
            params={"status": "all"},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 200, response.text
        assert response.json()["total"] == 2

    async def test_published_filter(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        await self._seed_three(client, admin_token)
        response = client.get(
            "/v1/admin/collections",
            params={"status": "published"},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 1
        assert body["collections"][0]["title"] == "Pub"

    async def test_draft_filter(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        await self._seed_three(client, admin_token)
        response = client.get(
            "/v1/admin/collections",
            params={"status": "draft"},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 1
        assert body["collections"][0]["title"] == "Draft"


class TestGetAndReplaceBooks:
    async def test_get_by_id_includes_all_books_even_unpublished(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        books = await _seed_books(test_session, count=2)
        published_book, draft_book = books[0], books[1]

        created = client.post(
            "/v1/admin/collections",
            json={"title": "Curadoria"},
            headers=_auth_headers(admin_token),
        ).json()

        # Replace with both books (one published, one not).
        replace = client.put(
            f"/v1/admin/collections/{created['id']}/books",
            json={"book_ids": [str(draft_book.id), str(published_book.id)]},
            headers=_auth_headers(admin_token),
        )
        assert replace.status_code == 200, replace.text
        body = replace.json()
        # Order preserved per request order; positions are 0,1.
        assert [b["slug"] for b in body["books"]] == ["livro-1", "livro-0"]
        assert [b["position"] for b in body["books"]] == [0, 1]
        # D10 — unpublished book IS present in the admin payload, flagged.
        by_slug = {b["slug"]: b for b in body["books"]}
        assert by_slug["livro-1"]["published"] is False
        assert by_slug["livro-0"]["published"] is True

        # GET by id returns the same.
        got = client.get(
            f"/v1/admin/collections/{created['id']}",
            headers=_auth_headers(admin_token),
        )
        assert got.status_code == 200, got.text
        assert [b["slug"] for b in got.json()["books"]] == ["livro-1", "livro-0"]

    async def test_replace_with_unknown_book_id_422(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        created = client.post(
            "/v1/admin/collections",
            json={"title": "X"},
            headers=_auth_headers(admin_token),
        ).json()
        missing = "00000000-0000-0000-0000-000000000000"
        response = client.put(
            f"/v1/admin/collections/{created['id']}/books",
            json={"book_ids": [missing]},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 422, response.text
        assert response.json() == {"detail": f"book not found: {missing}"}

    async def test_replace_empty_clears_collection(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        books = await _seed_books(test_session, count=1)
        created = client.post(
            "/v1/admin/collections",
            json={"title": "X"},
            headers=_auth_headers(admin_token),
        ).json()
        client.put(
            f"/v1/admin/collections/{created['id']}/books",
            json={"book_ids": [str(books[0].id)]},
            headers=_auth_headers(admin_token),
        )
        response = client.put(
            f"/v1/admin/collections/{created['id']}/books",
            json={"book_ids": []},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 200, response.text
        assert response.json()["books"] == []


class TestAuthGate:
    def test_create_without_token_401(self, client: TestClient) -> None:
        response = client.post(
            "/v1/admin/collections", json={"title": "x"}
        )
        assert response.status_code == 401

    def test_list_without_token_401(self, client: TestClient) -> None:
        response = client.get("/v1/admin/collections")
        assert response.status_code == 401
