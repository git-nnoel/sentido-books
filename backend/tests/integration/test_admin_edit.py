"""Integration tests for the curator edit + publish endpoints (B5).

Covers:
    * ``PUT /v1/admin/books/{id}`` — partial updates, unknown-field
      rejection, empty-patch rejection.
    * ``POST /v1/admin/books/{id}/publish`` — happy path and the
      embedding-pending gate.

These tests exercise the full request path: route → admin service →
catalog service → Postgres. No external HTTP / LLM clients are
involved at this layer (the edits don't call out), so we only need to
pin the app's sessionmaker to the integration test engine.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from sentido.catalog.models import AuthorORM, BookORM
from sentido.main import create_app

_VEC: list[float] = [0.01] * 1536


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(test_engine: AsyncEngine) -> Iterator[TestClient]:
    """Build a TestClient pinned to the integration test engine.

    The lifespan-built httpx + openai clients are left untouched —
    edit endpoints do not call out — so we only override the
    sessionmaker so writes land in ``sentido_test``.
    """
    app = create_app()
    with TestClient(app) as tc:
        app.state.sessionmaker = async_sessionmaker(
            test_engine, expire_on_commit=False
        )
        yield tc


async def _seed_book(
    test_session,
    *,
    slug: str = "o-estrangeiro",
    title: str = "O Estrangeiro",
    published: bool = False,
    embedding_status: str = "done",
    profile_status: str = "approved",
    with_embedding: bool = True,
) -> BookORM:
    """Insert a publish-ready book by default; tweak per test."""
    author = AuthorORM(slug="albert-camus", name="Albert Camus")
    test_session.add(author)
    await test_session.flush()

    book = BookORM(
        slug=slug,
        title=title,
        author_id=author.id,
        year_published=1942,
        synopsis="seed synopsis",
        emotional_profile=None,
        atmosphere_tags=[],
        narrative_pace=None,
        embedding=_VEC if with_embedding else None,
        embedding_status=embedding_status,
        profile_status=profile_status,
        published=published,
    )
    test_session.add(book)
    await test_session.commit()
    return book


# ---------------------------------------------------------------------------
# PUT /v1/admin/books/{id}
# ---------------------------------------------------------------------------


class TestEditEndpoint:
    async def test_put_books_id_updates_fields(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        book = await _seed_book(
            test_session,
            published=False,
            embedding_status="done",
            profile_status="approved",
        )

        response = client.put(
            f"/v1/admin/books/{book.id}",
            json={"synopsis": "edited synopsis", "atmosphere_tags": ["luz fria"]},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["synopsis"] == "edited synopsis"
        assert body["atmosphere_tags"] == ["luz fria"]
        # Unrelated fields unchanged.
        assert body["title"] == "O Estrangeiro"
        assert body["published"] is False

    async def test_put_books_id_extra_field_rejected(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        book = await _seed_book(test_session)
        response = client.put(
            f"/v1/admin/books/{book.id}",
            json={"synopsis": "ok", "unknown_field": "nope"},
            headers=_auth_headers(admin_token),
        )
        # Pydantic ``extra="forbid"`` → 422 (FastAPI request validation).
        assert response.status_code == 422, response.text

    async def test_put_books_id_empty_patch_rejected(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        book = await _seed_book(test_session)
        response = client.put(
            f"/v1/admin/books/{book.id}",
            json={},
            headers=_auth_headers(admin_token),
        )
        # The model_validator raises ValueError which Pydantic surfaces
        # at validation time → 422 (FastAPI wraps validators in a
        # request-validation error). Our global handler only catches
        # ValueErrors that escape past validation. Either status code
        # is acceptable per the plan — the contract is "empty patch is
        # an error", not a specific code. We assert non-2xx and that
        # the body carries a detail.
        assert response.status_code in (400, 422), response.text
        # The Pydantic envelope shape differs from our 400 shape but
        # both carry some detail-like payload.
        assert response.json()  # body is non-empty


# ---------------------------------------------------------------------------
# POST /v1/admin/books/{id}/publish
# ---------------------------------------------------------------------------


class TestPublishEndpoint:
    async def test_post_publish_succeeds(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        book = await _seed_book(
            test_session,
            published=False,
            embedding_status="done",
            profile_status="pending",  # publish endpoint flips this to approved
        )
        response = client.post(
            f"/v1/admin/books/{book.id}/publish",
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["published"] is True
        assert body["profile_status"] == "approved"
        assert body["embedding_status"] == "done"

    async def test_post_publish_422_when_embedding_pending(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        book = await _seed_book(
            test_session,
            published=False,
            embedding_status="pending",
            profile_status="pending",
            with_embedding=False,
        )
        response = client.post(
            f"/v1/admin/books/{book.id}/publish",
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 422
        assert response.json() == {
            "detail": "cannot publish: profile not approved or embedding missing"
        }
