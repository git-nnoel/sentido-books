"""End-to-end smoke covering the full Phase 0 lifecycle.

One test walks the entire flow with all externals mocked:
    1. POST /v1/admin/books/ingest          (Open Library mocked via httpx)
    2. POST /v1/admin/books/{id}/generate   (OpenAI mocked at the wrapper)
    3. PUT  /v1/admin/books/{id}            (approve only — still unpublished)
    4. POST /v1/admin/books/{id}/publish    (publishes)
    5. GET  /v1/books/{slug}                (public detail)
    6. POST /v1/search                      (semantic search)

The OpenAI fake routes by prompt content (system message keyword) so
the same fixture serves synopsis, profile, embedding, query embedding,
and resonance-line calls.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from sentido.main import create_app

# ---------------------------------------------------------------------------
# Canonical payloads.
# ---------------------------------------------------------------------------

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
            "large": "https://covers.openlibrary.org/b/id/8-L.jpg",
        },
        "works": [{"key": "/works/OL1234W"}],
    }
}

_SYNOPSIS_TEXT = (
    "Meursault não chora no funeral da mãe. O sol arde; as horas escorrem. "
    "Há um disparo na praia."
)

_PROFILE_JSON = (
    '{"anguish": 6.0, "melancholy": 4.0, "hope": 1.0, "violence": 5.0, '
    '"tenderness": 1.0, "strangeness": 8.5, '
    '"atmosphere_tags": ["apatia", "absurdo", "sol como violência"], '
    '"narrative_pace": "progressive"}'
)

_RESONANCE_LINE = "Meursault não chora; a recusa de sentir é a sua forma de existir."

_EMBEDDING: list[float] = [0.01] * 1536


# ---------------------------------------------------------------------------
# Open Library HTTP fake.
# ---------------------------------------------------------------------------


def _ol_handler(request: httpx.Request) -> httpx.Response:
    bibkeys = request.url.params.get("bibkeys", "")
    if bibkeys in _OL_PAYLOAD:
        return httpx.Response(200, json=_OL_PAYLOAD)
    return httpx.Response(404, json={})


# ---------------------------------------------------------------------------
# OpenAI fake.
# ---------------------------------------------------------------------------


class _Msg:
    def __init__(self, content: str) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str) -> None:
        self.message = _Msg(content)


class _ChatResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_Choice(content)]


class _EmbedItem:
    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding


class _EmbedResponse:
    def __init__(self, embedding: list[float]) -> None:
        self.data = [_EmbedItem(embedding)]


class _StubChatCompletions:
    def __init__(self, parent: "_FakeAsyncOpenAI") -> None:
        self._parent = parent

    async def create(self, **kwargs: Any) -> _ChatResponse:
        system = kwargs.get("messages", [{}])[0].get("content", "")
        self._parent.chat_call_count += 1
        if "sinopse" in system.lower():
            return _ChatResponse(_SYNOPSIS_TEXT)
        if "dimensões" in system.lower() or "json estrito" in system.lower():
            return _ChatResponse(_PROFILE_JSON)
        if "ressoa" in system.lower():
            return _ChatResponse(_RESONANCE_LINE)
        # Defensive fallback.
        return _ChatResponse("")


class _StubChat:
    def __init__(self, parent: "_FakeAsyncOpenAI") -> None:
        self.completions = _StubChatCompletions(parent)


class _StubEmbeddings:
    def __init__(self, parent: "_FakeAsyncOpenAI") -> None:
        self._parent = parent

    async def create(self, **kwargs: Any) -> _EmbedResponse:
        self._parent.embed_call_count += 1
        return _EmbedResponse(list(_EMBEDDING))


class _FakeAsyncOpenAI:
    """Minimum substitute for :class:`openai.AsyncOpenAI`.

    Routes chat calls by the system-message keyword so synopsis,
    profile, and resonance calls all share one fixture. Tracks call
    counts for debug / sanity checks.
    """

    def __init__(self) -> None:
        self.chat = _StubChat(self)
        self.embeddings = _StubEmbeddings(self)
        self.chat_call_count = 0
        self.embed_call_count = 0

    async def close(self) -> None:  # called by lifespan shutdown
        return None


# ---------------------------------------------------------------------------
# App fixture.
# ---------------------------------------------------------------------------


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def app_client(
    test_engine: AsyncEngine,
) -> Iterator[tuple[TestClient, _FakeAsyncOpenAI]]:
    """TestClient with both Open Library + OpenAI faked, DB pinned to test."""
    app = create_app()
    with TestClient(app) as client:
        # Pin sessionmaker to the integration test engine.
        app.state.sessionmaker = async_sessionmaker(
            test_engine, expire_on_commit=False
        )
        # Replace httpx_client with the mock-transport variant.
        app.state.httpx_client = httpx.AsyncClient(
            transport=httpx.MockTransport(_ol_handler)
        )
        # Replace openai_client with the fake.
        fake_openai = _FakeAsyncOpenAI()
        app.state.openai_client = fake_openai  # type: ignore[assignment]
        yield client, fake_openai


class TestFullFlow:
    def test_phase_0_lifecycle(
        self,
        app_client: tuple[TestClient, _FakeAsyncOpenAI],
        admin_token: str,
        test_session: Any,  # noqa: ARG002 — depended on for the truncate side-effect
    ) -> None:
        # The ``test_session`` fixture truncates catalog + resonance_cache
        # before yielding; depending on it here guarantees a clean DB
        # regardless of how this test sits in the run order.
        client, fake_openai = app_client

        # ----- 1. Ingest -------------------------------------------------
        r1 = client.post(
            "/v1/admin/books/ingest",
            json={"isbn": "9788501062451"},
            headers=_auth_headers(admin_token),
        )
        assert r1.status_code == 201, r1.text
        book = r1.json()
        book_id = book["id"]
        slug = book["slug"]
        assert book["embedding_status"] == "pending"
        assert book["published"] is False

        # ----- 2. Generate -----------------------------------------------
        r2 = client.post(
            f"/v1/admin/books/{book_id}/generate",
            headers=_auth_headers(admin_token),
        )
        assert r2.status_code == 200, r2.text
        gen = r2.json()
        assert gen["synopsis"].startswith("Meursault")
        assert gen["embedding_status"] == "done"
        assert gen["profile_status"] == "pending"
        assert gen["published"] is False

        # ----- 3. Approve via PUT (still unpublished) --------------------
        r3 = client.put(
            f"/v1/admin/books/{book_id}",
            json={"profile_status": "approved"},
            headers=_auth_headers(admin_token),
        )
        assert r3.status_code == 200, r3.text
        approved = r3.json()
        assert approved["profile_status"] == "approved"
        assert approved["published"] is False

        # ----- 4. Publish ------------------------------------------------
        r4 = client.post(
            f"/v1/admin/books/{book_id}/publish",
            headers=_auth_headers(admin_token),
        )
        assert r4.status_code == 200, r4.text
        pub = r4.json()
        assert pub["published"] is True
        assert pub["profile_status"] == "approved"

        # ----- 5. Public detail by slug ----------------------------------
        r5 = client.get(f"/v1/books/{slug}")
        assert r5.status_code == 200, r5.text
        detail = r5.json()
        assert detail["slug"] == slug
        assert detail["title"] == "O Estrangeiro"
        assert detail["author"]["slug"] == "albert-camus"
        assert detail["synopsis"].startswith("Meursault")
        assert detail["emotional_profile"]["anguish"] == 6.0
        assert detail["narrative_pace"] == "progressive"
        # No admin-only fields leak.
        for forbidden in ("id", "embedding_status", "profile_status", "published"):
            assert forbidden not in detail

        # ----- 6. Semantic search ----------------------------------------
        r6 = client.post(
            "/v1/search",
            json={"q": "solidão que não dói"},
        )
        assert r6.status_code == 200, r6.text
        search = r6.json()
        assert search["query"] == "solidão que não dói"
        assert len(search["results"]) >= 1
        first = search["results"][0]
        assert first["slug"] == slug
        assert first["resonance_line"] == _RESONANCE_LINE
        assert first["similarity"] == pytest.approx(1.0, abs=1e-4)
