"""Generation pure helpers.

Plan §3.2 / skill §3.2: **no I/O lives here.** The functions in this
module are deterministic data → data transforms that the service uses
to validate LLM payloads and compose the embedding source text. If any
helper grew an OpenAI call or a DB read, it would belong in
``service.py`` instead.

Two responsibilities:

* **Parse + validate the §4.2 profile JSON** returned by the LLM. The
  prompt asks for a *flat* JSON object — six axes plus
  ``atmosphere_tags`` and ``narrative_pace``. We unflatten it into the
  internal :class:`GeneratedProfileResult` so the service can read each
  piece without poking at dict keys.

* **Compose the embedding source text** (plan §11 D2). One PT-BR
  string, deterministic given inputs.
"""

from __future__ import annotations

import json

from pydantic import ValidationError

from sentido.generation.schemas import (
    EmotionalProfile,
    GeneratedProfileResult,
)

__all__ = [
    "clean_atmosphere_tags",
    "compose_embedding_text",
    "parse_profile",
]

# Plan §4.2 — exactly these six axes.
_PROFILE_AXES = (
    "anguish",
    "melancholy",
    "hope",
    "violence",
    "tenderness",
    "strangeness",
)

# Atmosphere tag bounds — mirror voice.md §4.2 ("3 a 5 termos curtos").
_MAX_TAGS = 5


def clean_atmosphere_tags(raw: list[str]) -> list[str]:
    """Normalize a raw atmosphere-tags list from the LLM.

    Steps:
        1. Strip whitespace around each entry.
        2. Lowercase (voice.md §4.2 requires lowercase tags).
        3. Drop empty strings.
        4. Cap to the first five entries (the upper bound; the lower
           bound of three is enforced downstream by the Pydantic
           schema, so an underrun surfaces as a validation error).

    Pure, deterministic. The service applies this *before* validating
    with :class:`GeneratedProfileResult` so the schema's ``min_length``
    check operates on the cleaned shape.
    """
    cleaned: list[str] = []
    for tag in raw:
        if not isinstance(tag, str):  # pragma: no cover — guarded by JSON shape
            continue
        normalized = tag.strip().lower()
        if not normalized:
            continue
        cleaned.append(normalized)
    return cleaned[:_MAX_TAGS]


def parse_profile(json_str: str) -> GeneratedProfileResult:
    """Parse the §4.2 LLM response into a validated result.

    Expected JSON shape (flat object)::

        {
          "anguish": 6.0,
          "melancholy": 4.0,
          "hope": 1.0,
          "violence": 5.0,
          "tenderness": 1.0,
          "strangeness": 8.5,
          "atmosphere_tags": ["apatia", "absurdo", "sol como violência"],
          "narrative_pace": "progressive"
        }

    On any deviation — malformed JSON, missing axis, out-of-range
    value, wrong ``narrative_pace`` literal, extra/missing top-level
    keys — raises ``ValueError`` with a short message. The service
    translates that into ``ApiError(502, ...)`` so the curator gets a
    Bad Gateway rather than a 500.

    Extra keys outside the known set are ignored (we only pull the
    fields we care about), not rejected — the LLM occasionally adds a
    rationale field we don't need.
    """
    try:
        payload = json.loads(json_str)
    except json.JSONDecodeError as exc:
        raise ValueError(f"profile json invalid: {exc.msg}") from exc

    if not isinstance(payload, dict):
        raise ValueError("profile json must be an object")

    # Build the six-axis subset. Missing/wrong-type values flow through
    # to Pydantic for a uniform error message.
    profile_payload = {axis: payload.get(axis) for axis in _PROFILE_AXES}

    tags_raw = payload.get("atmosphere_tags", [])
    if not isinstance(tags_raw, list):
        raise ValueError("atmosphere_tags must be a list")

    tags = clean_atmosphere_tags(tags_raw)

    try:
        profile = EmotionalProfile.model_validate(profile_payload)
        return GeneratedProfileResult(
            profile=profile,
            atmosphere_tags=tags,
            narrative_pace=payload.get("narrative_pace"),  # type: ignore[arg-type]
        )
    except ValidationError as exc:
        # Surface a short, single-line summary — the full Pydantic
        # report is too verbose for an HTTP detail string.
        errors = exc.errors()
        first = errors[0] if errors else {"msg": "validation failed"}
        loc = ".".join(str(x) for x in first.get("loc", [])) or "?"
        msg = first.get("msg", "invalid")
        raise ValueError(f"profile validation failed at {loc}: {msg}") from exc


def compose_embedding_text(
    *,
    title: str,
    author_name: str,
    synopsis: str,
    atmosphere_tags: list[str],
    narrative_pace: str,
) -> str:
    """Compose the deterministic embedding-source string (plan §11 D2).

    Shape::

        {title} — {author_name}. {synopsis}
        Atmosfera: {atmosphere_tags joined by ", "}.
        Ritmo: {narrative_pace}.

    A single string. Three lines, with a newline between the synopsis
    line and the ``Atmosfera`` line, and between ``Atmosfera`` and
    ``Ritmo``. Determinism is the point — re-running with identical
    inputs produces identical embedding vectors, which keeps the
    catalog reproducible across regenerations.

    The atmosphere tags are joined as-is (no re-cleaning here). Callers
    are expected to pass already-cleaned tags from
    :func:`clean_atmosphere_tags`.
    """
    tags_joined = ", ".join(atmosphere_tags)
    return (
        f"{title} — {author_name}. {synopsis}\n"
        f"Atmosfera: {tags_joined}.\n"
        f"Ritmo: {narrative_pace}."
    )
