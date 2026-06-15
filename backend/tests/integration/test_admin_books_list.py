"""Integration tests for ``GET /v1/admin/books`` (B5+ admin queue).

Covers the four status filters in plan §5.2 — ``pending_generation``,
``pending_approval``, ``published``, ``all`` — plus pagination and the
inherited ``require_admin`` gate. The endpoint hits route → admin
service → catalog service → Postgres; no external HTTP/LLM clients are
involved, so we only override the app's sessionmaker so writes land in
``sentido_test`` (mirrors ``test_admin_edit.py``).
"""

from __future__ import annotations

import datetime as dt
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
    """TestClient pinned to the integration test engine."""
    app = create_app()
    with TestClient(app) as tc:
        app.state.sessionmaker = async_sessionmaker(
            test_engine, expire_on_commit=False
        )
        yield tc


async def _seed_queue(test_session) -> None:
    """Insert four books spanning the admin status matrix.

    ``updated_at`` is set explicitly so ordering assertions are stable
    regardless of insert order — the published rows are the most
    recent, the pending_generation row is the oldest.
    """
    author = AuthorORM(slug="albert-camus", name="Albert Camus")
    test_session.add(author)
    await test_session.flush()

    base = dt.datetime(2026, 6, 1, 12, 0, tzinfo=dt.UTC)

    rows = [
        # 1) pending_generation: no embedding yet.
        BookORM(
            slug="livro-a",
            title="Livro A",
            author_id=author.id,
            embedding=None,
            embedding_status="pending",
            profile_status="pending",
            published=False,
            updated_at=base,
        ),
        # 2) pending_approval: embedding done, profile still pending.
        BookORM(
            slug="livro-b",
            title="Livro B",
            author_id=author.id,
            embedding=_VEC,
            embedding_status="done",
            profile_status="pending",
            published=False,
            updated_at=base + dt.timedelta(hours=1),
        ),
        # 3) published (approved + embedding done + published).
        BookORM(
            slug="livro-c",
            title="Livro C",
            author_id=author.id,
            embedding=_VEC,
            embedding_status="done",
            profile_status="approved",
            published=True,
            updated_at=base + dt.timedelta(hours=2),
        ),
        # 4) another published row — gives us two for the published filter
        #    and lets us check limit=1 still reports total=2.
        BookORM(
            slug="livro-d",
            title="Livro D",
            author_id=author.id,
            embedding=_VEC,
            embedding_status="done",
            profile_status="approved",
            published=True,
            updated_at=base + dt.timedelta(hours=3),
        ),
    ]
    for row in rows:
        test_session.add(row)
    await test_session.commit()


class TestListAdminBooks:
    async def test_default_status_is_pending_generation(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        await _seed_queue(test_session)
        response = client.get(
            "/v1/admin/books",
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 1
        assert len(body["books"]) == 1
        assert body["books"][0]["slug"] == "livro-a"
        assert body["books"][0]["embedding_status"] == "pending"

    async def test_pending_approval_filter(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        await _seed_queue(test_session)
        response = client.get(
            "/v1/admin/books",
            params={"status": "pending_approval"},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 1
        assert [b["slug"] for b in body["books"]] == ["livro-b"]

    async def test_published_filter(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        await _seed_queue(test_session)
        response = client.get(
            "/v1/admin/books",
            params={"status": "published"},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 2
        assert len(body["books"]) == 2
        # updated_at DESC — livro-d (newest) before livro-c.
        assert [b["slug"] for b in body["books"]] == ["livro-d", "livro-c"]

    async def test_all_filter_returns_every_row(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        await _seed_queue(test_session)
        response = client.get(
            "/v1/admin/books",
            params={"status": "all"},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 4
        assert len(body["books"]) == 4

    async def test_pagination_reports_unpaginated_total(
        self,
        client: TestClient,
        test_session,
        admin_token: str,
    ) -> None:
        await _seed_queue(test_session)
        response = client.get(
            "/v1/admin/books",
            params={"status": "published", "limit": 1},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 2
        assert len(body["books"]) == 1
        # First page = most recently updated published row.
        assert body["books"][0]["slug"] == "livro-d"

    def test_missing_token_returns_401(self, client: TestClient) -> None:
        response = client.get("/v1/admin/books")
        assert response.status_code == 401
