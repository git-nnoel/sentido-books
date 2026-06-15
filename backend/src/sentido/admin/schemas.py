"""Admin DTOs — the curator-facing book shape and request bodies.

Plan §5.2: every admin endpoint that returns a book returns the
**admin book shape**: the public ``BookDetailResponse`` plus
``id``, ``embedding_status``, ``profile_status``, ``published``,
``created_at``, ``updated_at``. Public endpoints never expose those
six fields (D4).

This module re-exports :class:`sentido.ingestion.schemas.IngestRequest`
so admin routes can import it from a single admin-facing namespace.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from sentido.catalog.models import BookORM
from sentido.catalog.schemas import (
    AuthorSummary,
    BookDetailResponse,
    EditionResponse,
    EmotionalProfile,
    NarrativePace,
)
from sentido.ingestion.schemas import IngestRequest

__all__ = [
    "AdminBookListResponse",
    "AdminBookResponse",
    "BookEditRequest",
    "IngestRequest",
]


EmbeddingStatus = Literal["pending", "done"]
ProfileStatus = Literal["pending", "approved", "rejected"]


class AdminBookResponse(BookDetailResponse):
    """Admin book shape — public payload + curator-only audit fields.

    The shape mirrors plan §5.2 exactly. ``related_books`` is always
    ``[]`` until embeddings exist (B4); the field stays on the contract
    so the admin frontend can render the same component as the public
    page once data is available.
    """

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    embedding_status: EmbeddingStatus
    profile_status: ProfileStatus
    published: bool
    created_at: dt.datetime
    updated_at: dt.datetime

    @classmethod
    def from_orm(cls, book: BookORM) -> "AdminBookResponse":
        """Build an :class:`AdminBookResponse` from a hydrated BookORM.

        Requires that ``book.author`` and ``book.editions`` are already
        loaded (use ``catalog.service.get_book_for_admin`` or the
        eager-loaded result of ``create_book_from_normalized``);
        otherwise SQLAlchemy will raise on lazy-load against a closed
        session.

        ``related_books`` is hard-coded to ``[]`` for now — B4 wires
        pgvector similarity to populate it.
        """
        profile = (
            EmotionalProfile.model_validate(book.emotional_profile)
            if book.emotional_profile is not None
            else None
        )

        author = AuthorSummary(slug=book.author.slug, name=book.author.name)

        editions = [
            EditionResponse(
                publisher=edition.publisher,
                language=edition.language,
                year=edition.year,
                isbn=edition.isbn,
            )
            for edition in book.editions
        ]

        return cls(
            id=book.id,
            slug=book.slug,
            title=book.title,
            original_title=book.original_title,
            year_published=book.year_published,
            author=author,
            synopsis=book.synopsis,
            emotional_profile=profile,
            atmosphere_tags=list(book.atmosphere_tags or []),
            narrative_pace=book.narrative_pace,  # type: ignore[arg-type]
            cover_url=book.cover_url,
            editions=editions,
            related_books=[],
            embedding_status=book.embedding_status,  # type: ignore[arg-type]
            profile_status=book.profile_status,  # type: ignore[arg-type]
            published=book.published,
            created_at=book.created_at,
            updated_at=book.updated_at,
        )


class BookEditRequest(BaseModel):
    """Partial-update request body for ``PUT /v1/admin/books/{id}`` (plan §5.2).

    All fields are optional — missing keys mean "do not change". Unknown
    keys are rejected with 422 via ``extra="forbid"`` (matching the
    plan's "Other fields rejected with 422" requirement). An all-empty
    body is rejected with a 400 (via ``ValueError``) by the
    :meth:`_require_at_least_one_field` validator.

    The publish gate ("setting ``published=true`` requires
    ``profile_status=approved`` and ``embedding_status=done``") is NOT
    enforced here — it runs against the post-patch state inside
    :func:`sentido.catalog.service.update_book` so that a single PATCH
    can both approve and publish atomically.
    """

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    original_title: str | None = None
    synopsis: str | None = None
    emotional_profile: EmotionalProfile | None = None
    atmosphere_tags: list[str] | None = None
    narrative_pace: NarrativePace | None = None
    cover_url: str | None = None
    year_published: int | None = None
    profile_status: Literal["pending", "approved", "rejected"] | None = None
    published: bool | None = None

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> "BookEditRequest":
        """Reject an all-empty patch (no fields set by the caller).

        Pydantic v2 does not differentiate "field omitted" from "field
        set to None" on the validated instance, so this validator
        inspects ``model_fields_set`` — the set of keys actually present
        in the incoming JSON. If none were present, the patch carries
        no instruction and we surface a 400 via the global handler
        (``ValueError`` → ``{"detail": "no fields to update"}``).
        """
        if not self.model_fields_set:
            raise ValueError("no fields to update")
        return self


class AdminBookListResponse(BaseModel):
    """List payload for ``GET /v1/admin/books`` (plan §5.2).

    The page envelope carries the slice of books matching the requested
    filter plus the *unpaginated* total — the admin panel uses ``total``
    to drive its pagination controls without a second round-trip.
    """

    model_config = ConfigDict(extra="forbid")

    books: list[AdminBookResponse]
    total: int
