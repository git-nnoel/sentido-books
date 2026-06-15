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

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    "AdminCollection",
    "AdminCollectionBook",
    "AdminCollectionListResponse",
    "BookEditRequest",
    "CollectionBooksReplaceRequest",
    "CollectionCreateRequest",
    "CollectionEditRequest",
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


# ---------------------------------------------------------------------------
# Collections — admin DTOs (plan §14.2 / §14.4)
# ---------------------------------------------------------------------------


class AdminCollectionBook(BaseModel):
    """A book entry inside an admin collection detail (plan §14.4).

    Carries the curator-facing shape: the book ``id`` (admin URLs use
    UUIDs, D5), its ``position`` in the collection, and its ``published``
    status so the curator knows what readers will actually see (D10).
    This is distinct from the public ``RelatedBook`` shape, which never
    exposes ``id``/``position``/``published``.
    """

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    slug: str
    title: str
    author_name: str
    position: int
    published: bool


class AdminCollection(BaseModel):
    """Admin collection shape (plan §14.4).

    Returned by every admin collection endpoint that yields a single
    collection (create, update, get-by-id, replace-books). ``books``
    includes ALL books in the collection regardless of publish state
    (D10) so the curator can compose and reorder drafts.
    """

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    slug: str
    title: str
    description: str | None = None
    published: bool
    created_at: dt.datetime
    updated_at: dt.datetime
    books: list[AdminCollectionBook] = Field(default_factory=list)


class AdminCollectionListResponse(BaseModel):
    """List payload for ``GET /v1/admin/collections`` (plan §14.2).

    Mirrors :class:`AdminBookListResponse`: the slice of collections
    matching the status filter plus the unpaginated ``total``.
    """

    model_config = ConfigDict(extra="forbid")

    collections: list[AdminCollection]
    total: int


class CollectionCreateRequest(BaseModel):
    """Request body for ``POST /v1/admin/collections`` (plan §14.2).

    ``title`` is required (min length 1). ``description`` is optional and
    nullable. The slug is derived server-side from ``title`` via
    :func:`sentido.catalog.logic.slugify` (slugs are never user-edited,
    plan §4.3).
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    description: str | None = None


class CollectionEditRequest(BaseModel):
    """Partial-update body for ``PUT /v1/admin/collections/{id}`` (plan §14.2).

    All fields optional — missing keys mean "do not change". Unknown
    keys → 422 via ``extra="forbid"``. An all-empty body is rejected by
    the :meth:`_require_at_least_one_field` validator, mirroring
    :class:`BookEditRequest`. ``model_dump(exclude_unset=True)`` is what
    crosses the route → service boundary so "field omitted" stays
    distinct from "field set to None" (a valid clear of ``description``).
    """

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    published: bool | None = None

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> "CollectionEditRequest":
        """Reject an all-empty patch (no fields set by the caller).

        Same rationale as :meth:`BookEditRequest._require_at_least_one_field`:
        Pydantic v2 cannot tell "omitted" from "set to None" on the
        validated instance, so we inspect ``model_fields_set``.
        """
        if not self.model_fields_set:
            raise ValueError("no fields to update")
        return self


class CollectionBooksReplaceRequest(BaseModel):
    """Request body for ``PUT /v1/admin/collections/{id}/books`` (plan §14.2).

    The curator UI sends the full ordered list on every save (D9); the
    service replaces all ``collection_books`` rows transactionally. An
    empty list is valid and clears the collection.
    """

    model_config = ConfigDict(extra="forbid")

    book_ids: list[uuid.UUID] = Field(default_factory=list)
