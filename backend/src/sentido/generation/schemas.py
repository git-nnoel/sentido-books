"""Generation DTOs (request body + parsed LLM responses).

The emotional-profile *axis* shape is the same one persisted via the
public contract — see :class:`sentido.catalog.schemas.EmotionalProfile`.
We import it directly rather than redeclaring the six axes in two
places: the contract is a single source of truth (plan §4.2) and the
LLM response must match it byte-for-byte to land in the database.

``GeneratedProfileResult`` carries the full §4.2 payload — the six
axes plus ``atmosphere_tags`` (3–5 short PT-BR lowercase strings) and
``narrative_pace`` (one of ``slow`` | ``progressive`` | ``frenetic``).
That superset only exists here in ``generation``; the public
``BookDetailResponse`` flattens the axes back out alongside the tags
and pace fields persisted directly on ``BookORM``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

# Reuse the contract's emotional-profile schema so any drift would
# surface as a single change site. Plan §4.2 / catalog.schemas docstring.
from sentido.catalog.schemas import EmotionalProfile, NarrativePace

__all__ = [
    "EmotionalProfile",
    "GenerationRequest",
    "GeneratedProfileResult",
    "NarrativePace",
]


class GenerationRequest(BaseModel):
    """Request body for ``POST /v1/admin/books/{id}/generate``.

    ``regenerate`` defaults to ``False``; sending ``{}`` (or omitting
    the body entirely) yields the safe behavior — refuse to overwrite
    existing artifacts. Set ``True`` to force overwrite, which also
    resets ``profile_status`` to ``"pending"`` so curator approval is
    required again (plan §5.2).
    """

    model_config = ConfigDict(extra="forbid")

    regenerate: bool = False


class GeneratedProfileResult(BaseModel):
    """Parsed payload returned by the §4.2 emotional-profile prompt.

    Validation rules (enforced by Pydantic):
        * ``profile`` — strict 6-axis ``EmotionalProfile``; out-of-range
          values are rejected.
        * ``atmosphere_tags`` — 3 to 5 short PT-BR lowercase strings.
          Whitespace + casing normalization happens *before* validation
          via :func:`sentido.generation.logic.clean_atmosphere_tags`.
        * ``narrative_pace`` — exactly one of ``slow`` |
          ``progressive`` | ``frenetic``.

    The tag count bounds mirror voice.md §4.2 ("3 a 5 termos"). We do
    not enforce the lowercase rule at the schema level — cleaning is
    done in pure logic so the validation message stays simple if the
    LLM returns malformed shapes.
    """

    model_config = ConfigDict(extra="forbid")

    profile: EmotionalProfile
    atmosphere_tags: list[str] = Field(min_length=3, max_length=5)
    narrative_pace: NarrativePace
