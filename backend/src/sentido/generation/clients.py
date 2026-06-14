"""OpenAI client wrapper with retry + per-call model selection.

Plan §3.2 / §3.3 (M8): all OpenAI SDK calls funnel through this
wrapper. The service constructs an :class:`OpenAIClient` per workflow
around the shared ``AsyncOpenAI`` instance built once in the app
lifespan (``main.lifespan`` → ``app.state.openai_client``).

**Retry policy** (plan §7.1): three attempts with exponential backoff
1s → 2s → 4s on :class:`openai.RateLimitError` and
:class:`openai.APIConnectionError`. Any other exception propagates
immediately. We implement the loop directly rather than reach for
``tenacity`` — plan §2 keeps the dep list minimal.

**Per-call configuration**: model + temperature + max_tokens come from
``service.py`` via keyword args. The constants in this module document
the plan §7.1 defaults but are not enforced at the client level — the
service is the source of truth for which model is used for which
artifact.
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from openai import APIConnectionError, AsyncOpenAI, RateLimitError

__all__ = [
    "EMBEDDING_MODEL",
    "EMOTIONAL_PROFILE_RESPONSE_FORMAT",
    "EMOTIONAL_PROFILE_TEMPERATURE",
    "GENERATION_MODEL",
    "OpenAIClient",
    "RESONANCE_LINE_MAX_TOKENS",
    "RESONANCE_LINE_TEMPERATURE",
    "SYNOPSIS_MAX_TOKENS",
    "SYNOPSIS_TEMPERATURE",
]

# --- Plan §7.1 defaults -------------------------------------------------
# The service passes these via kwargs to ``OpenAIClient.chat``. Keeping
# them in module constants (and not in ``schemas.py``, where they would
# be out of place) makes the call sites short and the policy visible
# in one location for review.

GENERATION_MODEL = "gpt-4o-mini"
EMBEDDING_MODEL = "text-embedding-3-small"

SYNOPSIS_TEMPERATURE = 0.7
SYNOPSIS_MAX_TOKENS = 400

EMOTIONAL_PROFILE_TEMPERATURE = 0.3
EMOTIONAL_PROFILE_RESPONSE_FORMAT: dict[str, str] = {"type": "json_object"}

RESONANCE_LINE_TEMPERATURE = 0.6
RESONANCE_LINE_MAX_TOKENS = 80

# Retry schedule per plan §7.1: three total attempts; on transient
# failure the wrapper sleeps before the next try. The 4.0s entry is
# the (currently unused) next-step delay, kept here so the schedule
# matches the plan's wording even though the third failure re-raises
# without an additional sleep.
_MAX_ATTEMPTS = 3
_RETRY_DELAYS_SECONDS: tuple[float, ...] = (1.0, 2.0, 4.0)

_log = structlog.get_logger(__name__)


class OpenAIClient:
    """Thin async wrapper around :class:`AsyncOpenAI`.

    One instance per ingest/generate call. The instance holds no
    mutable state beyond the underlying SDK client; the wrapper exists
    purely to centralize the retry policy and to give the service one
    seam to mock in tests.
    """

    def __init__(self, openai_async_client: AsyncOpenAI) -> None:
        self._client = openai_async_client

    async def chat(
        self,
        *,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        """Send a chat completion and return the first choice's text.

        The retry policy in :meth:`_with_retry` covers transient
        OpenAI failures. Any non-transient error (auth, bad request,
        SDK serialization) propagates so the service can translate it
        into a 502 with a short detail string.
        """
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if response_format is not None:
            kwargs["response_format"] = response_format

        async def _call() -> str:
            response = await self._client.chat.completions.create(**kwargs)
            # ``response.choices`` is non-empty in practice; if the SDK
            # ever returns an empty list we want to fail loudly rather
            # than silently emit an empty string.
            if not response.choices:
                raise ValueError("openai chat response had no choices")
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("openai chat response had no content")
            return content

        return await self._with_retry(_call, op="chat")

    async def embed(self, text: str) -> list[float]:
        """Return the embedding vector for ``text`` (1536 floats)."""

        async def _call() -> list[float]:
            response = await self._client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text,
            )
            if not response.data:
                raise ValueError("openai embed response had no data")
            return list(response.data[0].embedding)

        return await self._with_retry(_call, op="embed")

    async def _with_retry(self, fn: Any, *, op: str) -> Any:
        """Run ``fn`` with the plan §7.1 retry schedule.

        Three attempts total. On transient failure (RateLimitError,
        APIConnectionError) the wrapper sleeps 1s before attempt 2 and
        2s before attempt 3. A third failed attempt re-raises (the 4s
        entry in the documented schedule would be the next sleep if
        the policy ever grew to four attempts).

        Only :class:`RateLimitError` and :class:`APIConnectionError`
        are retried. Anything else — including SDK auth, malformed
        request errors, and our own ``ValueError`` from empty choices
        — propagates on first hit.
        """
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            try:
                return await fn()
            except (RateLimitError, APIConnectionError) as exc:
                if attempt == _MAX_ATTEMPTS:
                    _log.warning(
                        "openai.retry.exhausted",
                        op=op,
                        attempt=attempt,
                        error_type=type(exc).__name__,
                        error=str(exc)[:200],
                    )
                    raise
                delay = _RETRY_DELAYS_SECONDS[attempt - 1]
                _log.warning(
                    "openai.retry",
                    op=op,
                    attempt=attempt,
                    next_delay_s=delay,
                    error_type=type(exc).__name__,
                    error=str(exc)[:200],
                )
                await asyncio.sleep(delay)
        # Unreachable — the loop either returns or raises. Guard for
        # type-checkers.
        raise AssertionError(  # pragma: no cover
            "unreachable: retry loop exited without return/raise"
        )
