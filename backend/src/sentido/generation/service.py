"""Generation service — the imperative shell for LLM artifact creation.

Plan §6 / §3.2 / §3.3 (M3, M8): all OpenAI calls and DB writes that
generation needs live here. Pure validation + composition lives in
:mod:`sentido.generation.logic`. The catalog read path
(``catalog.service.get_book_for_admin``) is the only place this module
touches outside its own files.

One public function — :func:`generate_artifacts` — performs the full
synopsis → emotional profile → embedding workflow inside a single
session, committed atomically at the end. A partial generation never
lands: any failure between OpenAI calls returns 502 with the book row
untouched.
"""

from __future__ import annotations

import datetime as dt
import uuid

from openai import APIError, OpenAIError
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.catalog import service as catalog_service
from sentido.catalog.models import BookORM
from sentido.generation import prompts
from sentido.generation.clients import (
    EMOTIONAL_PROFILE_RESPONSE_FORMAT,
    EMOTIONAL_PROFILE_TEMPERATURE,
    GENERATION_MODEL,
    SYNOPSIS_MAX_TOKENS,
    SYNOPSIS_TEMPERATURE,
    OpenAIClient,
)
from sentido.generation.logic import (
    compose_embedding_text,
    parse_profile,
)
from sentido.shared.errors import ApiError


def _short(message: str, *, limit: int = 200) -> str:
    """Truncate an upstream error message for inclusion in HTTP detail."""
    if len(message) <= limit:
        return message
    return message[: limit - 1].rstrip() + "…"


def _has_existing_artifacts(book: BookORM) -> bool:
    """Return True if any of synopsis / profile / embedding is set."""
    return (
        book.synopsis is not None
        or book.emotional_profile is not None
        or book.embedding is not None
    )


async def generate_artifacts(
    *,
    session: AsyncSession,
    openai_client: OpenAIClient,
    book_id: uuid.UUID,
    regenerate: bool,
) -> BookORM:
    """Generate synopsis + emotional profile + embedding for a book.

    Workflow (plan §6):
        1. Load the BookORM via ``catalog.service.get_book_for_admin``
           — raises ``ApiError(404, "book not found")`` if missing.
        2. If ``regenerate`` is False and any artifact already exists,
           raise ``ApiError(409, ...)``.
        3. Call OpenAI for the **synopsis** (gpt-4o-mini, temperature
           0.7, max_tokens 400). Upstream errors → ``ApiError(502)``.
        4. Call OpenAI for the **emotional profile**
           (gpt-4o-mini, temperature 0.3, response_format=json_object).
           Parse + validate via :func:`logic.parse_profile`.
           ``ValueError`` → ``ApiError(502)``.
        5. Compose the embedding source string from the *new* synopsis
           + profile data — not the persisted (possibly stale) fields.
        6. Call OpenAI for the **embedding**
           (text-embedding-3-small). Errors → ``ApiError(502)``.
        7. Persist all artifacts in one transaction with the status
           flags reset per plan §5.2:
               * ``embedding_status = 'done'``
               * ``profile_status  = 'pending'``  (curator approval)
               * ``updated_at = now()``
        8. Reload with relations and return.
    """
    book = await catalog_service.get_book_for_admin(session, book_id)

    if not regenerate and _has_existing_artifacts(book):
        raise ApiError(
            409,
            "already generated; pass regenerate=true to overwrite",
        )

    title = book.title
    author_name = book.author.name
    year = book.year_published

    # --- 1) synopsis ---------------------------------------------------
    # We catch ``OpenAIError`` (the SDK base) for upstream API/transport
    # errors and ``ValueError`` for the wrapper's defensive empty-choice
    # guard. Both indicate the upstream failed to produce a usable
    # response and become a 502 to the caller.
    try:
        synopsis = await openai_client.chat(
            model=GENERATION_MODEL,
            system=prompts.SYNOPSIS_SYSTEM_PROMPT,
            user=prompts.synopsis_user_prompt(
                title=title, author=author_name, year=year
            ),
            temperature=SYNOPSIS_TEMPERATURE,
            max_tokens=SYNOPSIS_MAX_TOKENS,
        )
    except (OpenAIError, APIError, ValueError) as exc:
        raise ApiError(502, f"openai synopsis failed: {_short(str(exc))}") from exc

    synopsis = synopsis.strip()
    if not synopsis:
        raise ApiError(502, "openai synopsis failed: empty response")

    # --- 2) emotional profile -----------------------------------------
    try:
        profile_json = await openai_client.chat(
            model=GENERATION_MODEL,
            system=prompts.EMOTIONAL_PROFILE_SYSTEM_PROMPT,
            user=prompts.emotional_profile_user_prompt(
                title=title, author=author_name
            ),
            temperature=EMOTIONAL_PROFILE_TEMPERATURE,
            response_format=EMOTIONAL_PROFILE_RESPONSE_FORMAT,
        )
    except (OpenAIError, APIError, ValueError) as exc:
        raise ApiError(502, f"openai profile failed: {_short(str(exc))}") from exc

    try:
        result = parse_profile(profile_json)
    except ValueError as exc:
        raise ApiError(502, f"profile parsing failed: {_short(str(exc))}") from exc

    # --- 3) embedding -------------------------------------------------
    embedding_source = compose_embedding_text(
        title=title,
        author_name=author_name,
        synopsis=synopsis,
        atmosphere_tags=result.atmosphere_tags,
        narrative_pace=result.narrative_pace,
    )
    try:
        embedding = await openai_client.embed(embedding_source)
    except (OpenAIError, APIError, ValueError) as exc:
        raise ApiError(502, f"openai embedding failed: {_short(str(exc))}") from exc

    # --- 4) persist atomically ----------------------------------------
    # No prior writes have hit the session in this workflow, so a
    # single commit covers all three artifacts together. If commit
    # fails, none of the LLM output is persisted — the curator retries
    # the whole call. That trade is acceptable here because each
    # artifact independently costs <$0.01 in gpt-4o-mini tokens.
    book.synopsis = synopsis
    book.emotional_profile = result.profile.model_dump()
    book.atmosphere_tags = list(result.atmosphere_tags)
    book.narrative_pace = result.narrative_pace
    book.embedding = embedding
    book.embedding_status = "done"
    # ``regenerate=True`` resets curator approval per plan §5.2 — same
    # behavior as a first-time generation.
    book.profile_status = "pending"
    book.updated_at = dt.datetime.now(dt.UTC)

    await session.commit()

    # Reload with author + editions joined so the route can serialize
    # the AdminBookResponse without lazy loads on a closed session.
    return await catalog_service.get_book_for_admin(session, book_id)
