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
