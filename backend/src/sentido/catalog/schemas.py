"""Catalog Pydantic DTOs — public book/author shapes (plan §5.1).

These DTOs are the **public** contract consumed by the frontend. The
admin-specific extension (``AdminBookResponse``) lives in
:mod:`sentido.admin.schemas` because it adds curator-only fields
(``id``, ``embedding_status``, ``profile_status``, ``published``,
``created_at``, ``updated_at``) that public endpoints must never expose
(plan §5.2, D4).

Pydantic v2. ``model_config = ConfigDict(extra="forbid")`` to keep
unknown fields out of validated payloads.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AuthorSummary(BaseModel):
    """Compact author reference embedded inside a book detail payload."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str


class EditionResponse(BaseModel):
    """A single edition of a book (publisher, language, year, ISBN)."""

    model_config = ConfigDict(extra="forbid")

    publisher: str | None = None
    language: str | None = None
    year: int | None = None
    isbn: str | None = None


class RelatedBook(BaseModel):
    """Compact book reference used in the ``related_books`` array.

    Plan §5.1 lists slug, title, author_name, year_published, cover_url.
    ``slug``, ``title`` and ``author_name`` are always present; the
    visual fields may be missing for partially-ingested books.
    """

    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    author_name: str
    year_published: int | None = None
    cover_url: str | None = None


class EmotionalProfile(BaseModel):
    """Strict 6-axis emotional profile (plan §4.2).

    Every axis is required and clamped to ``[0.0, 10.0]``. Validation
    runs whenever a book payload is constructed from the ORM, so an
    invalid profile in the database fails loudly at serialization time
    rather than silently leaking past the contract.
    """

    model_config = ConfigDict(extra="forbid")

    anguish: float = Field(ge=0.0, le=10.0)
    melancholy: float = Field(ge=0.0, le=10.0)
    hope: float = Field(ge=0.0, le=10.0)
    violence: float = Field(ge=0.0, le=10.0)
    tenderness: float = Field(ge=0.0, le=10.0)
    strangeness: float = Field(ge=0.0, le=10.0)


NarrativePace = Literal["slow", "progressive", "frenetic"]


class BookDetailResponse(BaseModel):
    """Public ``GET /v1/books/{slug}`` payload (plan §5.1).

    The admin variant (``AdminBookResponse``) inherits from this and
    layers on the curator-only fields. Keep this shape stable — any
    change here is a contract change per plan §5 preamble.
    """

    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    original_title: str | None = None
    year_published: int | None = None
    author: AuthorSummary
    synopsis: str | None = None
    emotional_profile: EmotionalProfile | None = None
    atmosphere_tags: list[str] = Field(default_factory=list)
    narrative_pace: NarrativePace | None = None
    cover_url: str | None = None
    editions: list[EditionResponse] = Field(default_factory=list)
    related_books: list[RelatedBook] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Collections — public DTOs (plan §14.1 / §14.4)
# ---------------------------------------------------------------------------


class CollectionSummary(BaseModel):
    """Compact collection reference for ``GET /v1/collections`` (plan §14.1).

    The list envelope carries these summaries; the detail endpoint
    (:class:`CollectionDetail`) extends with the ordered book list.
    """

    model_config = ConfigDict(extra="forbid")

    slug: str
    title: str
    description: str | None = None


class CollectionListResponse(BaseModel):
    """Paginated list payload for ``GET /v1/collections`` (plan §14.1).

    ``total`` is the unpaginated count of published collections so the
    frontend can drive pagination without a second round-trip (mirrors
    :class:`sentido.admin.schemas.AdminBookListResponse`).
    """

    model_config = ConfigDict(extra="forbid")

    collections: list[CollectionSummary]
    total: int


class CollectionDetail(CollectionSummary):
    """Public ``GET /v1/collections/{slug}`` payload (plan §14.1).

    Extends :class:`CollectionSummary` with the ordered list of
    *published* books (unpublished books are filtered out to match the
    public-catalog visibility rule, plan §14.1 / D4). ``books`` reuses
    :class:`RelatedBook` — the same compact shape the rest of the public
    surface uses for book references.
    """

    model_config = ConfigDict(extra="forbid")

    books: list[RelatedBook] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Dimension navigation — public DTOs (plan §14.3 / §14.4)
# ---------------------------------------------------------------------------

# ``ExploreResult`` is the same compact book shape as ``RelatedBook``
# (plan §14.4 says "reuse the schema, alias if needed"). We alias rather
# than subclass so the contract documents the intent without a second
# class body to keep in sync.
ExploreResult = RelatedBook

ExploreMode = Literal["tag", "emotion", "pace"]


class ExploreResponse(BaseModel):
    """Payload for ``GET /v1/explore`` (plan §14.3).

    ``mode`` echoes the requested discriminator and ``value`` echoes the
    filter value (the tag string, the emotion axis, or the pace value)
    so the frontend can render the active-filter chrome from the
    response alone. Empty results are a 200 with ``results: []`` — never
    a 404 (plan §14.3).
    """

    model_config = ConfigDict(extra="forbid")

    mode: ExploreMode
    value: str
    results: list[ExploreResult] = Field(default_factory=list)
    total: int


class AtmosphereTagEntry(BaseModel):
    """A single aggregated atmosphere tag (plan §14.3)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    count: int


class AtmosphereTagsResponse(BaseModel):
    """Payload for ``GET /v1/explore/tags`` (plan §14.3).

    Drives the ``/explorar`` landing page. Tags are aggregated over
    published books, ordered by count DESC then name ASC, limited to 50.
    """

    model_config = ConfigDict(extra="forbid")

    tags: list[AtmosphereTagEntry] = Field(default_factory=list)
