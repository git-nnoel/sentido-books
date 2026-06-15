"""Public catalog routes (books, authors, collections).

Convention: this router uses ``prefix=""`` and individual endpoints
carry their own full ``/v1/...`` paths (e.g. ``/v1/books/{slug}``).
The same convention is used in :mod:`sentido.search.routes`. The admin
router is the only exception — it owns ``prefix="/v1/admin"`` so the
``require_admin`` dependency can be applied once at the router level
to every admin endpoint.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.catalog import service as catalog_service
from sentido.catalog.schemas import (
    AuthorSummary,
    BookDetailResponse,
    EditionResponse,
    EmotionalProfile,
    RelatedBook,
)
from sentido.shared.db import get_session

router = APIRouter(tags=["catalog"])


def _book_to_detail(book: object, related: list[object]) -> BookDetailResponse:
    """Build the public ``BookDetailResponse`` from a hydrated BookORM
    plus the pre-fetched related-books list.

    Both inputs are ``BookORM`` instances; the helper is typed as
    ``object`` to keep this module free of ORM imports that would bind
    the route to the persistence schema.
    """
    profile = (
        EmotionalProfile.model_validate(book.emotional_profile)  # type: ignore[attr-defined]
        if book.emotional_profile is not None  # type: ignore[attr-defined]
        else None
    )

    author = AuthorSummary(
        slug=book.author.slug,  # type: ignore[attr-defined]
        name=book.author.name,  # type: ignore[attr-defined]
    )

    editions = [
        EditionResponse(
            publisher=edition.publisher,
            language=edition.language,
            year=edition.year,
            isbn=edition.isbn,
        )
        for edition in book.editions  # type: ignore[attr-defined]
    ]

    related_books = [
        RelatedBook(
            slug=r.slug,  # type: ignore[attr-defined]
            title=r.title,  # type: ignore[attr-defined]
            author_name=r.author.name,  # type: ignore[attr-defined]
            year_published=r.year_published,  # type: ignore[attr-defined]
            cover_url=r.cover_url,  # type: ignore[attr-defined]
        )
        for r in related
    ]

    return BookDetailResponse(
        slug=book.slug,  # type: ignore[attr-defined]
        title=book.title,  # type: ignore[attr-defined]
        original_title=book.original_title,  # type: ignore[attr-defined]
        year_published=book.year_published,  # type: ignore[attr-defined]
        author=author,
        synopsis=book.synopsis,  # type: ignore[attr-defined]
        emotional_profile=profile,
        atmosphere_tags=list(book.atmosphere_tags or []),  # type: ignore[attr-defined]
        narrative_pace=book.narrative_pace,  # type: ignore[attr-defined]
        cover_url=book.cover_url,  # type: ignore[attr-defined]
        editions=editions,
        related_books=related_books,
    )


@router.get(
    "/v1/books/{slug}",
    response_model=BookDetailResponse,
    status_code=200,
)
async def get_book_by_slug(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> BookDetailResponse:
    """Public book detail (plan §5.1).

    Returns only published books — unpublished/unknown slugs return
    404 ``{"detail": "book not found"}`` per plan §5.1. The related
    books list comes from pgvector cosine similarity (plan §6) limited
    to 8 entries, also filtered to published rows only (D4).
    """
    book = await catalog_service.get_published_book_by_slug(session, slug)
    related = await catalog_service.find_related_books(session, book, limit=8)
    return _book_to_detail(book, related)
