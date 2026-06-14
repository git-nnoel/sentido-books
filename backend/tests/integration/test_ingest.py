"""Integration tests for ``POST /v1/admin/books/ingest``.

These tests exercise the full request path: route → admin service →
ingestion service → catalog service → Postgres. Open Library is faked
at the HTTP boundary via ``httpx.MockTransport`` (skill R15 Mode B —
external clients are stubbed at the network seam, the DB is real).

The shared httpx client lives on ``app.state.httpx_client``. To inject
the mock transport without rebuilding the lifespan we construct a
client wired to the transport and stash it on the app **after**
``TestClient`` starts the lifespan; the original is closed and
replaced. See ``mock_app`` below.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from sentido.main import create_app

# A realistic Open Library response shape for ISBN:9788501062451.
_OL_PAYLOAD = {
    "ISBN:9788501062451": {
        "url": "https://openlibrary.org/books/OL26321391M/O_Estrangeiro",
        "key": "/books/OL26321391M",
        "title": "O Estrangeiro",
        "authors": [
            {
                "url": "https://openlibrary.org/authors/OL2A/Albert_Camus",
                "name": "Albert Camus",
            }
        ],
        "publishers": [{"name": "Record"}],
        "publish_date": "2014",
        "cover": {
            "small": "https://covers.openlibrary.org/b/id/8-S.jpg",
            "medium": "https://covers.openlibrary.org/b/id/8-M.jpg",
            "large": "https://covers.openlibrary.org/b/id/8-L.jpg",
        },
        "works": [{"key": "/works/OL1234W"}],
    }
}


def _make_handler(
    responses: dict[str, httpx.Response],
) -> Callable[[httpx.Request], httpx.Response]:
    """Build a MockTransport handler that returns canned responses keyed
    by the ``bibkeys`` query parameter (``ISBN:...``).
    """

    def handler(request: httpx.Request) -> httpx.Response:
        bibkeys = request.url.params.get("bibkeys", "")
        if bibkeys in responses:
            return responses[bibkeys]
        return httpx.Response(404, json={})

    return handler


@pytest.fixture
def mock_app(
    test_engine: AsyncEngine,
) -> Iterator[tuple[TestClient, dict[str, httpx.Response]]]:
    """Build a TestClient whose httpx_client returns canned Open Library data.

    The fixture also pins the app's sessionmaker to the integration
    test engine so writes land in ``sentido_test``.
    """
    responses: dict[str, httpx.Response] = {}
    handler = _make_handler(responses)

    app = create_app()
    with TestClient(app) as client:
        # Replace the lifespan-built httpx client with one wired to
        # the mock transport. The original is closed via aclose() on
        # shutdown — closing here would race with TestClient's exit.
        mock_http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        app.state.httpx_client = mock_http

        # Pin the sessionmaker to the integration test engine.
        app.state.sessionmaker = async_sessionmaker(
            test_engine, expire_on_commit=False
        )

        yield client, responses


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestIngestHappyPath:
    def test_creates_book_returns_admin_shape(
        self,
        mock_app: tuple[TestClient, dict[str, httpx.Response]],
        admin_token: str,
    ) -> None:
        client, responses = mock_app
        responses["ISBN:9788501062451"] = httpx.Response(200, json=_OL_PAYLOAD)

        response = client.post(
            "/v1/admin/books/ingest",
            json={"isbn": "9788501062451"},
            headers=_auth_headers(admin_token),
        )

        assert response.status_code == 201, response.text
        body = response.json()
        # Public fields per plan §5.1.
        assert body["slug"] == "o-estrangeiro"
        assert body["title"] == "O Estrangeiro"
        assert body["author"]["slug"] == "albert-camus"
        assert body["author"]["name"] == "Albert Camus"
        assert body["year_published"] == 2014
        assert body["cover_url"] == "https://covers.openlibrary.org/b/id/8-L.jpg"
        assert body["synopsis"] is None
        assert body["emotional_profile"] is None
        assert body["atmosphere_tags"] == []
        assert body["narrative_pace"] is None
        # Editions list: one edition built from the ingest payload.
        assert len(body["editions"]) == 1
        assert body["editions"][0]["isbn"] == "9788501062451"
        assert body["editions"][0]["publisher"] == "Record"
        assert body["editions"][0]["year"] == 2014
        # Related_books deferred until B4 wires embeddings.
        assert body["related_books"] == []
        # Admin-only fields per plan §5.2.
        assert body["embedding_status"] == "pending"
        assert body["profile_status"] == "pending"
        assert body["published"] is False
        assert "id" in body
        assert "created_at" in body
        assert "updated_at" in body


class TestIngestDuplicate:
    def test_second_ingest_returns_409(
        self,
        mock_app: tuple[TestClient, dict[str, httpx.Response]],
        admin_token: str,
    ) -> None:
        client, responses = mock_app
        responses["ISBN:9788501062451"] = httpx.Response(200, json=_OL_PAYLOAD)

        first = client.post(
            "/v1/admin/books/ingest",
            json={"isbn": "9788501062451"},
            headers=_auth_headers(admin_token),
        )
        assert first.status_code == 201, first.text

        second = client.post(
            "/v1/admin/books/ingest",
            json={"isbn": "9788501062451"},
            headers=_auth_headers(admin_token),
        )
        assert second.status_code == 409
        assert second.json() == {"detail": "book already exists"}


class TestIngestNotFound:
    def test_unknown_isbn_returns_404(
        self,
        mock_app: tuple[TestClient, dict[str, httpx.Response]],
        admin_token: str,
    ) -> None:
        client, responses = mock_app
        responses["ISBN:9780000000002"] = httpx.Response(200, json={})

        response = client.post(
            "/v1/admin/books/ingest",
            json={"isbn": "9780000000002"},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "isbn not found"}

    def test_open_library_404_returns_404(
        self,
        mock_app: tuple[TestClient, dict[str, httpx.Response]],
        admin_token: str,
    ) -> None:
        client, _ = mock_app  # no canned response → handler returns 404
        response = client.post(
            "/v1/admin/books/ingest",
            json={"isbn": "9780000000019"},
            headers=_auth_headers(admin_token),
        )
        assert response.status_code == 404


class TestIngestInvalidIsbn:
    @pytest.mark.parametrize(
        "isbn",
        [
            "",
            "123",
            "abcdefghij",
            "12345678901234",  # 14 digits
        ],
    )
    def test_invalid_isbn_returns_400(
        self,
        mock_app: tuple[TestClient, dict[str, httpx.Response]],
        admin_token: str,
        isbn: str,
    ) -> None:
        client, _ = mock_app
        response = client.post(
            "/v1/admin/books/ingest",
            json={"isbn": isbn},
            headers=_auth_headers(admin_token),
        )
        # IngestRequest does NOT validate isbn shape — the service's
        # normalize_isbn raises ValueError, the global handler maps it
        # to HTTP 400 with {"detail": "<message>"}.
        assert response.status_code == 400, response.text
        assert "detail" in response.json()


class TestIngestRequiresAuth:
    def test_missing_token_returns_401(
        self,
        mock_app: tuple[TestClient, dict[str, httpx.Response]],
    ) -> None:
        client, _ = mock_app
        response = client.post(
            "/v1/admin/books/ingest",
            json={"isbn": "9788501062451"},
        )
        assert response.status_code == 401
        assert response.json() == {"detail": "unauthorized"}
