"""Public catalog routes (books, authors, collections).

Convention: this router uses ``prefix=""`` and individual endpoints
carry their own full ``/v1/...`` paths (e.g. ``/v1/books/{slug}``).
The same convention is used in :mod:`sentido.search.routes`. The admin
router is the only exception — it owns ``prefix="/v1/admin"`` so the
``require_admin`` dependency can be applied once at the router level
to every admin endpoint.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from sentido.catalog import service as catalog_service
from sentido.catalog.schemas import (
    AtmosphereTagEntry,
    AtmosphereTagsResponse,
    AuthorSummary,
    BookDetailResponse,
    CollectionDetail,
    CollectionListResponse,
    CollectionSummary,
    EditionResponse,
    EmotionalProfile,
    ExploreResponse,
    RelatedBook,
)
from sentido.shared.db import get_session
from sentido.shared.errors import ApiError

# The six emotion axes accepted by ``GET /v1/explore?mode=emotion``
# (plan §14.3 / §4.2). Declared here so the route can validate ``axis``
# before reaching the service.
_EMOTION_AXES = frozenset(
    {"anguish", "melancholy", "hope", "violence", "tenderness", "strangeness"}
)

# The three narrative paces accepted by ``mode=pace`` (plan §4.1 column).
_PACE_VALUES = frozenset({"slow", "progressive", "frenetic"})

router = APIRouter(tags=["catalog"])


def _book_to_related(book: object) -> RelatedBook:
    """Build a compact ``RelatedBook`` from a BookORM with author loaded.

    Reused by the collection-detail and explore routes — both render the
    public compact book shape. The input is a ``BookORM``; typed as
    ``object`` to keep this module free of ORM imports (same convention
    as :func:`_book_to_detail`).
    """
    return RelatedBook(
        slug=book.slug,  # type: ignore[attr-defined]
        title=book.title,  # type: ignore[attr-defined]
        author_name=book.author.name,  # type: ignore[attr-defined]
        year_published=book.year_published,  # type: ignore[attr-defined]
        cover_url=book.cover_url,  # type: ignore[attr-defined]
    )


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

    related_books = [_book_to_related(r) for r in related]

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


# ---------------------------------------------------------------------------
# Collections — public (plan §14.1)
# ---------------------------------------------------------------------------


@router.get(
    "/v1/collections",
    response_model=CollectionListResponse,
    status_code=200,
)
async def list_collections(
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=50)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CollectionListResponse:
    """List published collections (plan §14.1).

    Only ``published=True`` collections, ordered by ``updated_at DESC``.
    ``total`` is the unpaginated count so the frontend can render
    pagination without a second round-trip. An empty catalog is a 200
    with ``collections: []`` (not a 404).
    """
    collections, total = await catalog_service.list_published_collections(
        session, limit=limit, offset=offset
    )
    return CollectionListResponse(
        collections=[
            CollectionSummary(
                slug=c.slug,
                title=c.title,
                description=c.description,
            )
            for c in collections
        ],
        total=total,
    )


@router.get(
    "/v1/collections/{slug}",
    response_model=CollectionDetail,
    status_code=200,
)
async def get_collection_by_slug(
    slug: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CollectionDetail:
    """Public collection detail (plan §14.1).

    Returns 404 ``{"detail": "collection not found"}`` if the collection
    is missing or ``published=False``. ``books`` contains only published
    books, ordered by ``collection_books.position ASC``.
    """
    collection, books = await catalog_service.get_published_collection_by_slug(
        session, slug
    )
    return CollectionDetail(
        slug=collection.slug,
        title=collection.title,
        description=collection.description,
        books=[_book_to_related(b) for b in books],
    )


# ---------------------------------------------------------------------------
# Dimension navigation / explore — public (plan §14.3)
# ---------------------------------------------------------------------------


@router.get(
    "/v1/explore",
    response_model=ExploreResponse,
    status_code=200,
)
async def explore(
    session: Annotated[AsyncSession, Depends(get_session)],
    mode: Annotated[
        Literal["tag", "emotion", "pace"],
        Query(description="Discovery mode discriminator."),
    ],
    value: Annotated[
        str | None,
        Query(description="Filter value for mode=tag (the tag) or mode=pace."),
    ] = None,
    axis: Annotated[
        str | None,
        Query(description="Emotion axis for mode=emotion."),
    ] = None,
    min: Annotated[  # noqa: A002 — matches the contract query-param name.
        float,
        Query(ge=0.0, le=10.0, description="Minimum score for mode=emotion."),
    ] = 0.0,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ExploreResponse:
    """Multi-mode dimension navigation (plan §14.3, D8).

    A single endpoint with a ``mode`` discriminator dispatches to the
    tag / emotion / pace explore queries. All modes filter
    ``published=True``; ``mode=emotion`` additionally requires
    ``emotional_profile IS NOT NULL``. Empty results are a 200 with
    ``results: []`` — never a 404.

    Validation (400 via ``ApiError``):
        * ``mode=tag``   — ``value`` required.
        * ``mode=pace``  — ``value`` required, one of slow/progressive/frenetic.
        * ``mode=emotion`` — ``axis`` required, one of the six axes.

    (Invalid ``mode`` itself is rejected by FastAPI's ``Literal`` →
    422 before this handler runs.)
    """
    if mode == "tag":
        if not value:
            raise ApiError(400, "mode=tag requires a value")
        books, total = await catalog_service.explore_by_tag(
            session, tag=value, limit=limit, offset=offset
        )
        echo_value = value
    elif mode == "pace":
        if not value:
            raise ApiError(400, "mode=pace requires a value")
        if value not in _PACE_VALUES:
            raise ApiError(400, "mode=pace value must be slow, progressive, or frenetic")
        books, total = await catalog_service.explore_by_pace(
            session, pace=value, limit=limit, offset=offset
        )
        echo_value = value
    elif mode == "emotion":
        if not axis:
            raise ApiError(400, "mode=emotion requires an axis")
        if axis not in _EMOTION_AXES:
            raise ApiError(400, "mode=emotion axis is not a known emotion")
        books, total = await catalog_service.explore_by_emotion(
            session, axis=axis, min_score=min, limit=limit, offset=offset
        )
        echo_value = axis
    else:  # pragma: no cover — FastAPI's Literal guard makes this unreachable.
        raise ApiError(400, "invalid mode")

    return ExploreResponse(
        mode=mode,
        value=echo_value,
        results=[_book_to_related(b) for b in books],
        total=total,
    )


@router.get(
    "/v1/explore/tags",
    response_model=AtmosphereTagsResponse,
    status_code=200,
)
async def explore_tags(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AtmosphereTagsResponse:
    """Aggregated atmosphere tags over published books (plan §14.3).

    Drives the ``/explorar`` landing page. Ordered by count DESC then
    name ASC, limited to 50.
    """
    rows = await catalog_service.list_popular_atmosphere_tags(session, limit=50)
    return AtmosphereTagsResponse(
        tags=[AtmosphereTagEntry(name=name, count=count) for name, count in rows]
    )
