"""Integration tests for ``generation.service.generate_artifacts``.

Skill R15 (Mode B): the test DB is real (``sentido_test`` on the dev
Postgres container — fixtures live in ``backend/conftest.py``), but
OpenAI is stubbed at the **wrapper boundary**. Two stub styles are
used:

* :class:`_FakeOpenAIClient` — substitutes the entire
  :class:`OpenAIClient` wrapper. Used for happy-path / 409 /
  malformed-JSON tests where the retry behavior is irrelevant.
* :class:`_FakeAsyncOpenAI` — a minimum AsyncOpenAI replacement that
  feeds the **real** :class:`OpenAIClient` wrapper. Used for the
  retry-exercising test, so the production retry loop is the code
  under test rather than mocked away.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
import pytest_asyncio
from openai import APIConnectionError, RateLimitError
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.catalog.models import AuthorORM, BookORM
from sentido.generation import service as generation_service
from sentido.generation.clients import OpenAIClient
from sentido.shared.errors import ApiError

# ---------------------------------------------------------------------------
# Canonical canned LLM payloads.
# ---------------------------------------------------------------------------

_SYNOPSIS_TEXT = (
    "Meursault não chora no funeral da mãe. O sol arde; as horas escorrem. "
    "Há um disparo na praia. O que segue é um homem que recusa o teatro do "
    "sentimento — e descobre, no julgamento, que essa recusa é o seu crime."
)

_PROFILE_PAYLOAD = {
    "anguish": 6.0,
    "melancholy": 4.0,
    "hope": 1.0,
    "violence": 5.0,
    "tenderness": 1.0,
    "strangeness": 8.5,
    "atmosphere_tags": ["apatia", "absurdo", "sol como violência"],
    "narrative_pace": "progressive",
}

_PROFILE_JSON = json.dumps(_PROFILE_PAYLOAD)

# 1536-dim vector — text-embedding-3-small's output shape.
_EMBEDDING: list[float] = [0.01] * 1536


# ---------------------------------------------------------------------------
# Stubs.
# ---------------------------------------------------------------------------


class _FakeOpenAIClient:
    """Stand-in for :class:`OpenAIClient` that returns canned data.

    Exposes the same ``chat`` / ``embed`` signatures the service calls.
    Tracks call args so tests can assert on which prompts were sent.
    """

    def __init__(
        self,
        *,
        synopsis: str = _SYNOPSIS_TEXT,
        profile_json: str = _PROFILE_JSON,
        embedding: list[float] | None = None,
    ) -> None:
        self._synopsis = synopsis
        self._profile_json = profile_json
        self._embedding = embedding if embedding is not None else list(_EMBEDDING)
        self.chat_calls: list[dict[str, Any]] = []
        self.embed_calls: list[str] = []

    async def chat(self, **kwargs: Any) -> str:
        self.chat_calls.append(kwargs)
        system = kwargs["system"]
        if "sinopse" in system.lower():
            return self._synopsis
        if "dimensões" in system.lower() or "json estrito" in system.lower():
            return self._profile_json
        # Resonance prompt is not exercised by B4 — defensive fallback.
        return ""

    async def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return self._embedding


# --- Stub feeding the real OpenAIClient wrapper ---------------------------


class _StubChatCompletions:
    def __init__(self, parent: _FakeAsyncOpenAI) -> None:
        self._parent = parent

    async def create(self, **kwargs: Any) -> Any:
        return self._parent._next_chat_response(kwargs)


class _StubChat:
    def __init__(self, parent: _FakeAsyncOpenAI) -> None:
        self.completions = _StubChatCompletions(parent)


class _StubEmbeddings:
    def __init__(self, parent: _FakeAsyncOpenAI) -> None:
        self._parent = parent

    async def create(self, **kwargs: Any) -> Any:
        return self._parent._next_embed_response()


class _FakeAsyncOpenAI:
    """Minimum substitute for :class:`openai.AsyncOpenAI`.

    The real :class:`OpenAIClient` calls ``client.chat.completions.create``
    and ``client.embeddings.create``; this stub provides exactly those
    two seams plus a hook to script per-call behavior (raising on the
    first N attempts, then succeeding).
    """

    def __init__(self) -> None:
        self.chat = _StubChat(self)
        self.embeddings = _StubEmbeddings(self)
        self._chat_scripted_errors: list[Exception] = []
        self._embed_scripted_errors: list[Exception] = []
        self.chat_call_index = 0
        self.embed_call_index = 0

    def script_chat_errors(self, errors: list[Exception]) -> None:
        self._chat_scripted_errors = errors

    def script_embed_errors(self, errors: list[Exception]) -> None:
        self._embed_scripted_errors = errors

    def _next_chat_response(self, kwargs: dict[str, Any]) -> Any:
        idx = self.chat_call_index
        self.chat_call_index += 1
        if idx < len(self._chat_scripted_errors):
            raise self._chat_scripted_errors[idx]
        system = kwargs.get("messages", [{}])[0].get("content", "")
        if "json estrito" in system.lower():
            return _make_chat_response(_PROFILE_JSON)
        return _make_chat_response(_SYNOPSIS_TEXT)

    def _next_embed_response(self) -> Any:
        idx = self.embed_call_index
        self.embed_call_index += 1
        if idx < len(self._embed_scripted_errors):
            raise self._embed_scripted_errors[idx]
        return _make_embed_response(_EMBEDDING)


class _Msg:
    def __init__(self, content: str) -> None:
        self.content = content


class _Choice:
    def __init__(self, content: str) -> None:
        self.message = _Msg(content)


class _ChatResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_Choice(content)]


def _make_chat_response(content: str) -> _ChatResponse:
    return _ChatResponse(content)


class _EmbedItem:
    def __init__(self, embedding: list[float]) -> None:
        self.embedding = embedding


class _EmbedResponse:
    def __init__(self, embedding: list[float]) -> None:
        self.data = [_EmbedItem(embedding)]


def _make_embed_response(embedding: list[float]) -> _EmbedResponse:
    return _EmbedResponse(embedding)


# --- Helpers to build the canned exceptions ------------------------------


def _rate_limit_error(message: str = "rate limited") -> RateLimitError:
    """Construct a :class:`RateLimitError` without hitting the real API.

    The SDK's exception constructors require a ``response`` and ``body``;
    we build a stub httpx.Response that satisfies the signature.
    """
    response = httpx.Response(429, request=httpx.Request("POST", "https://stub"))
    return RateLimitError(message, response=response, body=None)


def _connection_error() -> APIConnectionError:
    return APIConnectionError(request=httpx.Request("POST", "https://stub"))


# ---------------------------------------------------------------------------
# Fixtures — fast event-loop friendly sleep (avoid 3s waits in retry tests).
# ---------------------------------------------------------------------------


@pytest.fixture
def fast_sleep(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[float]]:
    """Replace ``asyncio.sleep`` inside the clients module with a no-op
    that records every delay it would have slept for.

    Lets retry tests assert the schedule (1s, 2s) without elapsing
    real wall time.
    """
    recorded: list[float] = []

    async def _no_sleep(delay: float) -> None:
        recorded.append(delay)

    monkeypatch.setattr(
        "sentido.generation.clients.asyncio.sleep", _no_sleep, raising=True
    )
    yield recorded


# ---------------------------------------------------------------------------
# Seed helper.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def seeded_book(test_session: AsyncSession) -> BookORM:
    """Insert a minimal author + book into ``sentido_test``.

    Returns a BookORM in the same starting state ingest leaves behind
    (plan §9 B3): pending statuses, no synopsis, no embedding.
    """
    author = AuthorORM(slug="albert-camus", name="Albert Camus")
    test_session.add(author)
    await test_session.flush()

    book = BookORM(
        slug="o-estrangeiro",
        title="O Estrangeiro",
        author_id=author.id,
        year_published=1942,
        atmosphere_tags=[],
        embedding_status="pending",
        profile_status="pending",
        published=False,
    )
    test_session.add(book)
    await test_session.commit()
    return book


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


class TestGenerateArtifactsHappyPath:
    async def test_persists_all_three_artifacts(
        self,
        test_session: AsyncSession,
        seeded_book: BookORM,
    ) -> None:
        fake = _FakeOpenAIClient()
        result = await generation_service.generate_artifacts(
            session=test_session,
            openai_client=fake,  # type: ignore[arg-type]
            book_id=seeded_book.id,
            regenerate=False,
        )

        assert result.synopsis is not None
        assert result.synopsis.startswith("Meursault")
        assert result.emotional_profile == {
            "anguish": 6.0,
            "melancholy": 4.0,
            "hope": 1.0,
            "violence": 5.0,
            "tenderness": 1.0,
            "strangeness": 8.5,
        }
        assert result.atmosphere_tags == ["apatia", "absurdo", "sol como violência"]
        assert result.narrative_pace == "progressive"
        assert result.embedding is not None
        # pgvector returns a typed Vector; convert to list for comparison.
        assert list(result.embedding) == _EMBEDDING

        assert result.embedding_status == "done"
        assert result.profile_status == "pending"

        # Two chat calls (synopsis + profile) and one embed call.
        assert len(fake.chat_calls) == 2
        assert len(fake.embed_calls) == 1
        # The embedding source string draws from the NEW synopsis, not
        # any stale persisted value (plan §11 D2).
        embed_text = fake.embed_calls[0]
        assert "O Estrangeiro" in embed_text
        assert "Albert Camus" in embed_text
        assert "Atmosfera: apatia, absurdo, sol como violência." in embed_text
        assert "Ritmo: progressive." in embed_text


class TestGenerateArtifactsAlreadyGenerated:
    async def test_409_without_regenerate(
        self,
        test_session: AsyncSession,
        seeded_book: BookORM,
    ) -> None:
        # Pre-fill artifacts as if generation had already run.
        seeded_book.synopsis = "old synopsis"
        seeded_book.emotional_profile = {
            "anguish": 1.0,
            "melancholy": 1.0,
            "hope": 1.0,
            "violence": 1.0,
            "tenderness": 1.0,
            "strangeness": 1.0,
        }
        seeded_book.embedding = list(_EMBEDDING)
        seeded_book.embedding_status = "done"
        seeded_book.profile_status = "approved"
        await test_session.commit()

        fake = _FakeOpenAIClient()
        with pytest.raises(ApiError) as exc_info:
            await generation_service.generate_artifacts(
                session=test_session,
                openai_client=fake,  # type: ignore[arg-type]
                book_id=seeded_book.id,
                regenerate=False,
            )
        assert exc_info.value.status_code == 409
        assert "regenerate=true" in exc_info.value.detail

        # Nothing in the OpenAI client got called.
        assert fake.chat_calls == []
        assert fake.embed_calls == []

    async def test_regenerate_true_overwrites_and_resets_profile_status(
        self,
        test_session: AsyncSession,
        seeded_book: BookORM,
    ) -> None:
        seeded_book.synopsis = "old synopsis"
        seeded_book.emotional_profile = {
            "anguish": 1.0,
            "melancholy": 1.0,
            "hope": 1.0,
            "violence": 1.0,
            "tenderness": 1.0,
            "strangeness": 1.0,
        }
        seeded_book.embedding = list(_EMBEDDING)
        seeded_book.embedding_status = "done"
        seeded_book.profile_status = "approved"
        await test_session.commit()

        fake = _FakeOpenAIClient()
        result = await generation_service.generate_artifacts(
            session=test_session,
            openai_client=fake,  # type: ignore[arg-type]
            book_id=seeded_book.id,
            regenerate=True,
        )

        assert result.synopsis is not None
        assert result.synopsis.startswith("Meursault")
        assert result.profile_status == "pending"  # reset on regenerate
        assert result.embedding_status == "done"


class TestGenerateArtifactsBadProfileJson:
    async def test_malformed_profile_returns_502_no_writes(
        self,
        test_session: AsyncSession,
        seeded_book: BookORM,
    ) -> None:
        fake = _FakeOpenAIClient(profile_json="this is not json")

        with pytest.raises(ApiError) as exc_info:
            await generation_service.generate_artifacts(
                session=test_session,
                openai_client=fake,  # type: ignore[arg-type]
                book_id=seeded_book.id,
                regenerate=False,
            )
        assert exc_info.value.status_code == 502
        assert "profile parsing failed" in exc_info.value.detail

        # DB row is unchanged — no partial write landed.
        await test_session.rollback()
        await test_session.refresh(seeded_book)
        assert seeded_book.synopsis is None
        assert seeded_book.emotional_profile is None
        assert seeded_book.embedding is None
        assert seeded_book.embedding_status == "pending"
        assert seeded_book.profile_status == "pending"


class TestGenerateArtifactsRetry:
    async def test_recovers_after_two_rate_limit_errors(
        self,
        test_session: AsyncSession,
        seeded_book: BookORM,
        fast_sleep: list[float],
    ) -> None:
        """OpenAIClient.chat raises RateLimitError on attempts 1 + 2 of
        the *synopsis* call, then succeeds on attempt 3. Subsequent
        chat call (profile) and embed call run normally.

        Exercises the production retry loop end-to-end through the
        real :class:`OpenAIClient` wrapper.
        """
        fake_async = _FakeAsyncOpenAI()
        fake_async.script_chat_errors(
            [_rate_limit_error("retry me"), _rate_limit_error("retry me again")]
        )
        wrapper = OpenAIClient(fake_async)  # type: ignore[arg-type]

        result = await generation_service.generate_artifacts(
            session=test_session,
            openai_client=wrapper,
            book_id=seeded_book.id,
            regenerate=False,
        )

        assert result.synopsis is not None
        assert result.embedding_status == "done"
        # Two sleeps recorded — the 1s and 2s backoffs between attempts.
        assert fast_sleep[:2] == [1.0, 2.0]
        # 3 chat-create calls were made for the synopsis attempt (2
        # failures + 1 success), plus 1 for the profile call.
        assert fake_async.chat_call_index == 4
        assert fake_async.embed_call_index == 1

    async def test_connection_error_also_retried(
        self,
        test_session: AsyncSession,
        seeded_book: BookORM,
        fast_sleep: list[float],
    ) -> None:
        fake_async = _FakeAsyncOpenAI()
        fake_async.script_chat_errors([_connection_error()])
        wrapper = OpenAIClient(fake_async)  # type: ignore[arg-type]

        result = await generation_service.generate_artifacts(
            session=test_session,
            openai_client=wrapper,
            book_id=seeded_book.id,
            regenerate=False,
        )
        assert result.synopsis is not None
        assert fast_sleep[:1] == [1.0]
