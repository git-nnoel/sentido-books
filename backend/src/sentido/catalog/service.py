"""Catalog service — imperative shell for catalog reads/writes.

Plan §3.2 / skill §3.2: ``service.py`` is the only place inside the
catalog module where SQL runs. Pure transforms (slug derivation,
formatting) live in :mod:`sentido.catalog.logic`; data shapes for the
API live in :mod:`sentido.catalog.schemas`.

This module exposes the public surface other modules consume
(``ingestion``, ``admin``) per plan §3.3 — siblings import
``catalog.service`` and may also touch ``catalog.models`` ORM classes
for queries (M7).

The session-lifecycle convention follows the plan: writes go through
``session.flush()`` to populate generated IDs, and the orchestration
boundary (``admin.service``/``ingestion.service``) owns the single
``session.commit()`` for the whole workflow.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, func, select
from sqlalchemy import types as sqltypes
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import Select

from sentido.catalog.logic import slug_with_disambiguator, slugify
from sentido.catalog.models import (
    AuthorORM,
    BookORM,
    CollectionBookORM,
    CollectionORM,
    EditionORM,
)
from sentido.shared.errors import ApiError

if TYPE_CHECKING:
    from sentido.ingestion.schemas import NormalizedBook

# Maximum collision-resolution tries for slugs. After exhausting
# `-{lastname}` and `-2`..`-{_MAX_NUMERIC_SUFFIX}`, we give up and 500
# the request — that's a signal something's wrong with the input, not
# a normal case.
_MAX_NUMERIC_SUFFIX = 50


async def find_book_by_isbn(session: AsyncSession, isbn: str) -> BookORM | None:
    """Return the BookORM linked to ``isbn`` via an edition, or None.

    Used by ingestion to detect duplicates before fetching from Open
    Library (cheap guard) — and as a post-check when callers want to
    look a book up directly.
    """
    stmt = (
        select(BookORM)
        .join(EditionORM, EditionORM.book_id == BookORM.id)
        .where(EditionORM.isbn == isbn)
        .limit(1)
    )
    return await session.scalar(stmt)


async def find_or_create_author(
    session: AsyncSession,
    *,
    name: str,
    ol_author_id: str | None,
) -> AuthorORM:
    """Upsert an author by ``ol_author_id`` (preferred) or by
    case-insensitive name match.

    Notes on the matching strategy:
      - Open Library IDs are the strong key. When present we trust them
        and bypass name comparison entirely.
      - When no OL id is available we fall back to ``lower(name)`` —
        good enough for the curator's solo workflow (plan §3 / D3), but
        will collide for genuinely distinct people sharing a name. The
        ingestion plan documents this as an accepted v1 limitation.

    A new author gets a slug derived from :func:`logic.slugify`. On
    UNIQUE collision we try numeric suffixes ``-2``, ``-3``, … via
    :func:`logic.slug_with_disambiguator`.
    """
    name = name.strip()
    if not name:
        raise ValueError("author name is required")

    if ol_author_id:
        existing = await session.scalar(
            select(AuthorORM).where(AuthorORM.ol_id == ol_author_id).limit(1)
        )
        if existing is not None:
            return existing

    existing = await session.scalar(
        select(AuthorORM).where(func.lower(AuthorORM.name) == name.lower()).limit(1)
    )
    if existing is not None:
        # Backfill ol_id if we now know it and we didn't before.
        if ol_author_id and not existing.ol_id:
            existing.ol_id = ol_author_id
            await session.flush()
        return existing

    base = slugify(name) or "author"
    return await _insert_author_with_unique_slug(
        session, name=name, base_slug=base, ol_author_id=ol_author_id
    )


async def _insert_author_with_unique_slug(
    session: AsyncSession,
    *,
    name: str,
    base_slug: str,
    ol_author_id: str | None,
) -> AuthorORM:
    """Insert AuthorORM, choosing a non-colliding slug.

    Implementation note on the pre-check pattern:

    SQLAlchemy + asyncpg aborts the surrounding transaction on the
    first ``IntegrityError`` — we cannot loop ``flush`` to retry. So we
    pre-query the set of taken slugs from the candidate list and pick
    the first free one. The same pattern is used for books below.

    Candidate order:
        1. ``base_slug``
        2. ``base_slug-2``, ``base_slug-3``, …
    """
    candidates: list[str] = [base_slug]
    for n in range(2, _MAX_NUMERIC_SUFFIX + 1):
        candidates.append(slug_with_disambiguator(base_slug, str(n)))

    existing_slugs = set(
        (
            await session.scalars(
                select(AuthorORM.slug).where(AuthorORM.slug.in_(candidates))
            )
        ).all()
    )
    for candidate in candidates:
        if candidate in existing_slugs:
            continue
        author = AuthorORM(slug=candidate, name=name, ol_id=ol_author_id)
        session.add(author)
        try:
            await session.flush()
        except IntegrityError:
            # A concurrent insert grabbed the slug between SELECT and
            # INSERT. v1 is single-curator; surface loudly rather than
            # silently retrying with a broken transaction.
            await session.rollback()
            raise ApiError(500, "author slug collision could not be resolved") from None
        return author

    raise ApiError(500, "author slug collision could not be resolved")


async def create_book_from_normalized(
    session: AsyncSession, normalized: "NormalizedBook"
) -> BookORM:
    """Persist a new Book + Edition from a normalized ingestion payload.

    Steps (single session, no commit — caller commits):
      1. Resolve/create the **primary author** (the first entry in
         ``normalized.authors``). Multiple authors are a v1 limitation
         documented in plan §10 follow-up; we keep only the first.
      2. Insert ``BookORM`` with the plan §4 Phase-0 defaults:
         ``embedding_status='pending'``, ``profile_status='pending'``,
         ``published=False``. The slug starts from ``slugify(title)``
         and falls back to ``-{author_last_name}`` then ``-2``/``-3``/…
         on UNIQUE collision (plan §4.3).
      3. Insert one ``EditionORM`` from the ISBN/publisher/year/cover
         data carried by ``NormalizedBook``.
      4. Return the persisted ``BookORM`` with ``author`` and
         ``editions`` eagerly loaded so the route can serialize without
         additional round-trips.

    Slug-collision retries are bounded; if exhausted we raise a 500
    ``ApiError`` rather than loop forever.
    """
    if not normalized.authors:  # pragma: no cover — guarded at normalizer.
        raise ValueError("normalized book must have at least one author")

    primary = normalized.authors[0]
    author = await find_or_create_author(
        session, name=primary.name, ol_author_id=primary.ol_author_id
    )

    book = await _insert_book_with_unique_slug(
        session, normalized=normalized, author=author
    )

    edition = EditionORM(
        book_id=book.id,
        publisher=normalized.publishers[0] if normalized.publishers else None,
        language=None,
        year=normalized.publish_year,
        isbn=normalized.isbn,
        cover_url=normalized.cover_url,
    )
    session.add(edition)
    await session.flush()

    # Reload with eager author + editions so the response serializer can
    # walk the graph without triggering lazy loads on a closed session.
    return await _reload_book_with_relations(session, book.id)


async def _insert_book_with_unique_slug(
    session: AsyncSession,
    *,
    normalized: "NormalizedBook",
    author: AuthorORM,
) -> BookORM:
    """Insert BookORM, escalating slug candidates on UNIQUE collision.

    Candidate order (plan §4.3):
        1. ``slugify(title)``
        2. ``slug_with_disambiguator(base, author.last_name)``
        3. ``base-2``, ``base-3``, …
    """
    base = slugify(normalized.title) or "book"
    last_name = author.name.strip().rsplit(" ", 1)[-1]

    candidates: list[str] = [base]
    if last_name:
        candidates.append(slug_with_disambiguator(base, last_name))
    for n in range(2, _MAX_NUMERIC_SUFFIX + 1):
        candidates.append(slug_with_disambiguator(base, str(n)))

    # Pre-check existing slugs in one round-trip to avoid burning
    # transaction state on each failed flush — slug collisions abort
    # the transaction in Postgres.
    existing_slugs = set(
        (
            await session.scalars(
                select(BookORM.slug).where(BookORM.slug.in_(candidates))
            )
        ).all()
    )
    for candidate in candidates:
        if candidate in existing_slugs:
            continue
        book = BookORM(
            slug=candidate,
            title=normalized.title,
            original_title=None,
            author_id=author.id,
            year_published=normalized.publish_year,
            synopsis=None,
            emotional_profile=None,
            atmosphere_tags=[],
            narrative_pace=None,
            cover_url=normalized.cover_url,
            ol_id=normalized.ol_work_id,
            embedding=None,
            embedding_status="pending",
            profile_status="pending",
            published=False,
        )
        session.add(book)
        try:
            await session.flush()
        except IntegrityError:
            # A concurrent insert grabbed the slug between SELECT and
            # INSERT. Rolling back to a savepoint would let us retry,
            # but for v1 (solo curator) this is so unlikely that we
            # surface it loudly instead of silently retrying.
            await session.rollback()
            raise ApiError(500, "book slug collision could not be resolved") from None
        return book

    raise ApiError(500, "book slug collision could not be resolved")


async def _reload_book_with_relations(
    session: AsyncSession, book_id: uuid.UUID
) -> BookORM:
    stmt = (
        select(BookORM)
        .where(BookORM.id == book_id)
        .options(selectinload(BookORM.author), selectinload(BookORM.editions))
    )
    book = await session.scalar(stmt)
    if book is None:  # pragma: no cover — we just inserted this row.
        raise ApiError(500, "book vanished after insert")
    return book


async def get_book_for_admin(session: AsyncSession, book_id: uuid.UUID) -> BookORM:
    """Load a BookORM with author + editions joined.

    Raises ``ApiError(404, "book not found")`` if no row matches.
    Reused by ingestion (post-create) and by future B4/B5 admin
    workflows.
    """
    stmt = (
        select(BookORM)
        .where(BookORM.id == book_id)
        .options(selectinload(BookORM.author), selectinload(BookORM.editions))
    )
    book = await session.scalar(stmt)
    if book is None:
        raise ApiError(404, "book not found")
    return book


# Fields that the admin PATCH may set on a BookORM. Listed explicitly
# rather than derived from the request schema so a future schema change
# cannot accidentally widen what the service is willing to write —
# adding a field here is a conscious step.
_PATCHABLE_BOOK_FIELDS = frozenset(
    {
        "title",
        "original_title",
        "synopsis",
        "emotional_profile",
        "atmosphere_tags",
        "narrative_pace",
        "cover_url",
        "year_published",
        "profile_status",
        "published",
    }
)


async def update_book(
    session: AsyncSession,
    book_id: uuid.UUID,
    patch: dict[str, Any],
) -> BookORM:
    """Apply a partial update to a book row (plan §5.2).

    The caller (admin route) is expected to pass the result of
    ``BookEditRequest.model_dump(exclude_unset=True)`` so that "field
    not in the patch" and "field explicitly set to None" are
    distinguishable — keys present here are written, even when the
    value is ``None``.

    Publish gate (plan §5.2 / D4): the *post-patch* state must satisfy
    ``profile_status == "approved"`` AND ``embedding_status == "done"``
    if ``published`` is True. This allows a single PATCH that both
    approves and publishes a book in one call (used by
    :func:`sentido.admin.service.publish_book`). The check runs on the
    pending values before commit so a violating patch never lands.

    Raises:
        ApiError 404: book id not found.
        ApiError 422: publish gate violated.
    """
    book = await get_book_for_admin(session, book_id)

    # ``emotional_profile`` arrives as a Pydantic model when validated
    # via ``BookEditRequest``; serialize it to dict for the JSONB column.
    # Other complex fields (list, scalars) round-trip as-is.
    for key, value in patch.items():
        if key not in _PATCHABLE_BOOK_FIELDS:
            # Defensive: BookEditRequest has extra="forbid" so this is
            # unreachable from the HTTP path. Guard anyway so that
            # callers passing a hand-built dict cannot reach unrelated
            # ORM attributes.
            raise ApiError(422, f"field not editable: {key}")
        if key == "emotional_profile" and value is not None and hasattr(value, "model_dump"):
            value = value.model_dump()
        setattr(book, key, value)

    # Publish gate against the *post-patch* state.
    if book.published and (
        book.profile_status != "approved" or book.embedding_status != "done"
    ):
        raise ApiError(
            422,
            "cannot publish: profile not approved or embedding missing",
        )

    book.updated_at = dt.datetime.now(dt.UTC)

    await session.commit()
    return await get_book_for_admin(session, book_id)


async def list_admin_books(
    session: AsyncSession,
    *,
    status_filter: str,
    limit: int,
    offset: int,
) -> tuple[list[BookORM], int]:
    """Return a slice of books plus the matching total (plan §5.2).

    Filter semantics:
        * ``pending_generation`` — ``embedding_status == "pending"``
        * ``pending_approval``  — ``profile_status == "pending"`` AND
                                  ``embedding_status == "done"``
        * ``published``         — ``published == true``
        * ``all``               — no filter

    Any other value raises ``ApiError(400, "invalid status filter")``.

    Ordering is ``updated_at DESC`` so the admin panel queue surfaces
    the most recently touched books first. ``author`` + ``editions`` are
    eager-loaded so the route can serialize without lazy-load on a
    closed session (mirrors :func:`get_book_for_admin`). One query
    fetches the page, a second runs ``SELECT count(*)`` against the
    same WHERE clause for ``total``.
    """
    base = select(BookORM)
    if status_filter == "pending_generation":
        base = base.where(BookORM.embedding_status == "pending")
    elif status_filter == "pending_approval":
        base = base.where(BookORM.profile_status == "pending").where(
            BookORM.embedding_status == "done"
        )
    elif status_filter == "published":
        base = base.where(BookORM.published.is_(True))
    elif status_filter == "all":
        pass
    else:
        raise ApiError(400, "invalid status filter")

    page_stmt = (
        base.options(selectinload(BookORM.author), selectinload(BookORM.editions))
        .order_by(BookORM.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    books = list((await session.scalars(page_stmt)).all())

    count_stmt = select(func.count()).select_from(base.subquery())
    total = await session.scalar(count_stmt) or 0

    return books, int(total)


async def get_published_book_by_slug(session: AsyncSession, slug: str) -> BookORM:
    """Load a published BookORM by slug with author + editions joined.

    Plan §5.1 / D4: only books with ``published=True`` are visible to
    the public surface. Unpublished slugs (or unknown slugs) return
    404 — the same response — so the surface doesn't leak existence.
    """
    stmt = (
        select(BookORM)
        .where(BookORM.slug == slug)
        .where(BookORM.published.is_(True))
        .options(selectinload(BookORM.author), selectinload(BookORM.editions))
    )
    book = await session.scalar(stmt)
    if book is None:
        raise ApiError(404, "book not found")
    return book


async def find_related_books(
    session: AsyncSession,
    book: BookORM,
    limit: int = 8,
) -> list[BookORM]:
    """Return the most semantically similar published books.

    Plan §5.1: ``related_books`` is computed via pgvector cosine
    similarity against the input book's embedding, excluding the
    book itself, limited to 8 by default. Books with no embedding
    are skipped (they can't be ranked). If the input book itself has
    no embedding, returns ``[]``.

    Uses pgvector's cosine-distance operator (``<=>``) through
    :meth:`pgvector.sqlalchemy.Vector.cosine_distance`. The plan §4.1
    ``books_embedding_idx`` ivfflat index with ``vector_cosine_ops``
    covers this query.
    """
    if book.embedding is None:
        return []

    stmt = (
        select(BookORM)
        .where(BookORM.id != book.id)
        .where(BookORM.published.is_(True))
        .where(BookORM.embedding.is_not(None))
        .order_by(BookORM.embedding.cosine_distance(book.embedding))
        .limit(limit)
        .options(selectinload(BookORM.author))
    )
    result = await session.scalars(stmt)
    return list(result.all())


# ===========================================================================
# Collections (plan §14.1 / §14.2 / §14.5)
# ===========================================================================

# Collection slugs follow the same numeric-suffix collision pattern as
# books/authors (plan §14, "append -2, -3, … up to -50"). Reuses the
# module-level ``_MAX_NUMERIC_SUFFIX`` bound.


async def list_published_collections(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
) -> tuple[list[CollectionORM], int]:
    """Return a page of published collections plus the matching total.

    Plan §14.1: only ``published=True`` collections, ordered by
    ``updated_at DESC``. Two queries — one for the page, one for the
    unpaginated count — mirroring :func:`list_admin_books`.
    """
    base = select(CollectionORM).where(CollectionORM.published.is_(True))

    page_stmt = (
        base.order_by(CollectionORM.updated_at.desc()).limit(limit).offset(offset)
    )
    collections = list((await session.scalars(page_stmt)).all())

    count_stmt = select(func.count()).select_from(base.subquery())
    total = await session.scalar(count_stmt) or 0

    return collections, int(total)


async def get_published_collection_by_slug(
    session: AsyncSession, slug: str
) -> tuple[CollectionORM, list[BookORM]]:
    """Load a published collection + its published books, ordered.

    Plan §14.1:
      - 404 ``{"detail": "collection not found"}`` if the collection is
        missing or ``published=False`` (same response so the surface
        doesn't leak existence, mirroring book-by-slug, D4).
      - ``books`` only includes ``published=True`` books, ordered by
        ``collection_books.position ASC``.

    Returns the collection plus the ordered list of published books with
    ``author`` eager-loaded (the route needs ``author.name`` to build
    the ``RelatedBook`` shape).
    """
    collection = await session.scalar(
        select(CollectionORM)
        .where(CollectionORM.slug == slug)
        .where(CollectionORM.published.is_(True))
    )
    if collection is None:
        raise ApiError(404, "collection not found")

    books_stmt = (
        select(BookORM)
        .join(CollectionBookORM, CollectionBookORM.book_id == BookORM.id)
        .where(CollectionBookORM.collection_id == collection.id)
        .where(BookORM.published.is_(True))
        .order_by(CollectionBookORM.position.asc())
        .options(selectinload(BookORM.author))
    )
    books = list((await session.scalars(books_stmt)).all())

    return collection, books


async def create_collection(
    session: AsyncSession,
    *,
    title: str,
    description: str | None,
) -> CollectionORM:
    """Create a collection with a server-derived unique slug (plan §14.2).

    Slug derives from ``slugify(title)`` with numeric-suffix collision
    resolution (``-2``..``-50``), the same pattern used for books and
    authors. The caller (admin route) commits via this function — a
    single-statement write that is self-contained, so we commit here and
    reload to return a fully-populated row.
    """
    title = title.strip()
    if not title:
        raise ValueError("collection title is required")

    collection = await _insert_collection_with_unique_slug(
        session, title=title, description=description
    )
    await session.commit()
    return await _get_collection_orm(session, collection.id)


async def _insert_collection_with_unique_slug(
    session: AsyncSession,
    *,
    title: str,
    description: str | None,
) -> CollectionORM:
    """Insert CollectionORM, choosing a non-colliding slug.

    Same pre-check pattern as :func:`_insert_book_with_unique_slug`:
    Postgres aborts the transaction on the first ``IntegrityError``, so
    we pre-query taken slugs from the candidate list and pick the first
    free one.

    Candidate order (plan §14):
        1. ``slugify(title)``
        2. ``slugify(title)-2``, ``-3``, … up to ``-50``
    """
    base = slugify(title) or "collection"

    candidates: list[str] = [base]
    for n in range(2, _MAX_NUMERIC_SUFFIX + 1):
        candidates.append(slug_with_disambiguator(base, str(n)))

    existing_slugs = set(
        (
            await session.scalars(
                select(CollectionORM.slug).where(CollectionORM.slug.in_(candidates))
            )
        ).all()
    )
    for candidate in candidates:
        if candidate in existing_slugs:
            continue
        collection = CollectionORM(
            slug=candidate,
            title=title,
            description=description,
            published=False,
        )
        session.add(collection)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            raise ApiError(
                500, "collection slug collision could not be resolved"
            ) from None
        return collection

    raise ApiError(500, "collection slug collision could not be resolved")


# Fields the admin PATCH may set on a CollectionORM. Listed explicitly
# (not derived from the request schema) so a future schema change cannot
# silently widen what the service writes — mirrors ``_PATCHABLE_BOOK_FIELDS``.
_PATCHABLE_COLLECTION_FIELDS = frozenset({"title", "description", "published"})


async def update_collection(
    session: AsyncSession,
    collection_id: uuid.UUID,
    patch: dict[str, Any],
) -> CollectionORM:
    """Apply a partial update to a collection row (plan §14.2).

    The caller passes ``CollectionEditRequest.model_dump(exclude_unset=True)``
    so "field omitted" stays distinct from "field set to None" (clearing
    ``description``). The slug is never re-derived on title edits —
    slugs are stable across edits (D5).

    Raises ``ApiError(404, "collection not found")`` if the id is
    unknown.
    """
    collection = await _get_collection_orm(session, collection_id)

    for key, value in patch.items():
        if key not in _PATCHABLE_COLLECTION_FIELDS:
            # Defensive: CollectionEditRequest has extra="forbid" so this
            # is unreachable from the HTTP path. Guard against hand-built
            # dicts reaching unrelated ORM attributes.
            raise ApiError(422, f"field not editable: {key}")
        setattr(collection, key, value)

    collection.updated_at = dt.datetime.now(dt.UTC)

    await session.commit()
    return await _get_collection_orm(session, collection_id)


async def delete_collection(session: AsyncSession, collection_id: uuid.UUID) -> None:
    """Delete a collection (plan §14.2).

    Cascades to ``collection_books`` via the existing FK ON DELETE
    CASCADE constraint. Raises ``ApiError(404, "collection not found")``
    if the id is unknown so the route can return a clean 404 rather than
    a silent 204 for a non-existent collection.
    """
    collection = await _get_collection_orm(session, collection_id)
    await session.delete(collection)
    await session.commit()


async def list_admin_collections(
    session: AsyncSession,
    *,
    status_filter: str,
    limit: int,
    offset: int,
) -> tuple[list[CollectionORM], int]:
    """Return a page of collections (admin) plus the matching total.

    Plan §14.2 filter semantics:
        * ``published`` — ``published == true``
        * ``draft``     — ``published == false``
        * ``all``       — no filter

    Any other value raises ``ApiError(400, "invalid status filter")``.
    Ordered by ``updated_at DESC``. ``book_links`` (with each link's
    ``book.author``) is eager-loaded so the route can build the
    ``AdminCollection`` shape without lazy loads on a closed session.
    """
    base = select(CollectionORM)
    if status_filter == "published":
        base = base.where(CollectionORM.published.is_(True))
    elif status_filter == "draft":
        base = base.where(CollectionORM.published.is_(False))
    elif status_filter == "all":
        pass
    else:
        raise ApiError(400, "invalid status filter")

    page_stmt = (
        base.options(
            selectinload(CollectionORM.book_links)
            .selectinload(CollectionBookORM.book)
            .selectinload(BookORM.author)
        )
        .order_by(CollectionORM.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    collections = list((await session.scalars(page_stmt)).all())

    count_stmt = select(func.count()).select_from(base.subquery())
    total = await session.scalar(count_stmt) or 0

    return collections, int(total)


async def get_collection_for_admin(
    session: AsyncSession, collection_id: uuid.UUID
) -> CollectionORM:
    """Load a collection for admin with ALL its books eager-loaded.

    Plan §14.2 / D10: returns the collection with every book link
    (including unpublished books) so the curator can compose and reorder
    drafts. ``book_links`` are loaded with each link's ``book.author``;
    the route orders the entries by ``position``.

    Raises ``ApiError(404, "collection not found")`` if the id is
    unknown.
    """
    return await _get_collection_orm(session, collection_id)


async def replace_collection_books(
    session: AsyncSession,
    collection_id: uuid.UUID,
    book_ids: list[uuid.UUID],
) -> CollectionORM:
    """Replace the ordered set of books in a collection in one transaction.

    Plan §14.2 / D9 implementation:
      1. Validate the collection exists (404 if not).
      2. Validate every ``book_id`` exists; 422 with the first missing id
         if any is unknown.
      3. ``DELETE FROM collection_books WHERE collection_id = ?``
      4. ``INSERT`` one row per id at its array index as ``position``.

    All in a single transaction (one commit). An empty ``book_ids`` list
    is valid and clears the collection.

    Returns the refreshed collection (all books eager-loaded).
    """
    # 1. Collection must exist.
    collection = await _get_collection_orm(session, collection_id)

    # 2. Validate every book id exists. Preserve request order so the
    #    error reports the *first* missing id (plan §14.2). We fetch the
    #    set of known ids in one round-trip, then walk the request order.
    if book_ids:
        known = set(
            (
                await session.scalars(
                    select(BookORM.id).where(BookORM.id.in_(book_ids))
                )
            ).all()
        )
        for book_id in book_ids:
            if book_id not in known:
                raise ApiError(422, f"book not found: {book_id}")

    # 3. Clear existing links.
    await session.execute(
        delete(CollectionBookORM).where(
            CollectionBookORM.collection_id == collection_id
        )
    )

    # 4. Insert new links at their array index. ``book_ids`` may contain
    #    duplicates from a malformed client; the composite PK
    #    (collection_id, book_id) would reject those — but we de-dupe
    #    defensively while preserving first-seen order so a duplicate is
    #    a no-op rather than a 500.
    seen: set[uuid.UUID] = set()
    position = 0
    for book_id in book_ids:
        if book_id in seen:
            continue
        seen.add(book_id)
        session.add(
            CollectionBookORM(
                collection_id=collection_id,
                book_id=book_id,
                position=position,
            )
        )
        position += 1

    collection.updated_at = dt.datetime.now(dt.UTC)

    await session.commit()
    return await _get_collection_orm(session, collection_id)


async def _get_collection_orm(
    session: AsyncSession, collection_id: uuid.UUID
) -> CollectionORM:
    """Load a CollectionORM by id with all book links + authors joined.

    Raises ``ApiError(404, "collection not found")`` if no row matches.
    Shared by the admin collection ops — every one needs the fully
    hydrated row to build the ``AdminCollection`` response.

    ``expire_all`` is called first so a reload *after a write* truly
    re-reads the DB: with ``expire_on_commit=False`` the session keeps
    the identity-mapped parent and would otherwise hand back its
    previously-loaded (now stale) ``book_links`` collection instead of
    re-running the ``selectinload``. Expiring forces the relationship to
    repopulate from the committed rows.
    """
    session.expire_all()

    stmt = (
        select(CollectionORM)
        .where(CollectionORM.id == collection_id)
        .options(
            selectinload(CollectionORM.book_links)
            .selectinload(CollectionBookORM.book)
            .selectinload(BookORM.author)
        )
    )
    collection = await session.scalar(stmt)
    if collection is None:
        raise ApiError(404, "collection not found")
    return collection


# ===========================================================================
# Dimension navigation / explore (plan §14.3 / §14.5)
# ===========================================================================

# The six emotion axes (plan §4.2). Used to guard the JSONB key passed
# into the ``mode=emotion`` ORDER BY / filter so an arbitrary string can
# never reach the SQL expression.
_EMOTION_AXES = frozenset(
    {"anguish", "melancholy", "hope", "violence", "tenderness", "strangeness"}
)


async def explore_by_tag(
    session: AsyncSession,
    *,
    tag: str,
    limit: int,
    offset: int,
) -> tuple[list[BookORM], int]:
    """Published books carrying ``tag`` in ``atmosphere_tags`` (plan §14.3).

    Structural filter on the ``TEXT[]`` column — no embedding required.
    Ordered by ``updated_at DESC``. Returns the page plus the
    unpaginated total. Empty result is a normal ``([], 0)`` — the route
    surfaces it as a 200, not a 404.
    """
    base = (
        select(BookORM)
        .where(BookORM.published.is_(True))
        .where(BookORM.atmosphere_tags.any(tag))
    )
    return await _paginate_explore(session, base, limit=limit, offset=offset)


async def explore_by_emotion(
    session: AsyncSession,
    *,
    axis: str,
    min_score: float,
    limit: int,
    offset: int,
) -> tuple[list[BookORM], int]:
    """Published books scored on an emotion ``axis`` (plan §14.3).

    Filters ``published=True AND emotional_profile IS NOT NULL`` and
    ``(emotional_profile->>axis)::float >= min_score``. Ordered by
    ``(emotional_profile->>axis)::float DESC`` with ``updated_at DESC``
    as a tiebreak.

    ``axis`` MUST be one of the six known axes — the route validates
    this and we assert it here so an arbitrary string can never reach
    the JSONB key expression.
    """
    if axis not in _EMOTION_AXES:  # pragma: no cover — route validates first.
        raise ApiError(400, "invalid emotion axis")

    score = func.cast(
        BookORM.emotional_profile[axis].astext, sqltypes.Float
    )

    base = (
        select(BookORM)
        .where(BookORM.published.is_(True))
        .where(BookORM.emotional_profile.is_not(None))
        .where(score >= min_score)
    )
    page_stmt = (
        base.options(selectinload(BookORM.author))
        .order_by(score.desc(), BookORM.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    books = list((await session.scalars(page_stmt)).all())

    count_stmt = select(func.count()).select_from(base.subquery())
    total = await session.scalar(count_stmt) or 0

    return books, int(total)


async def explore_by_pace(
    session: AsyncSession,
    *,
    pace: str,
    limit: int,
    offset: int,
) -> tuple[list[BookORM], int]:
    """Published books with ``narrative_pace == pace`` (plan §14.3).

    Structural filter on the ``TEXT`` column — no embedding required.
    Ordered by ``updated_at DESC``. Returns the page plus the
    unpaginated total.
    """
    base = (
        select(BookORM)
        .where(BookORM.published.is_(True))
        .where(BookORM.narrative_pace == pace)
    )
    return await _paginate_explore(session, base, limit=limit, offset=offset)


async def _paginate_explore(
    session: AsyncSession,
    base: Select,
    *,
    limit: int,
    offset: int,
) -> tuple[list[BookORM], int]:
    """Apply the shared explore ordering + pagination to a filtered query.

    Used by tag/pace modes (both order by ``updated_at DESC``). The
    emotion mode builds its own ordering and does not route through
    here. ``author`` is eager-loaded so the route can build the
    ``ExploreResult`` (``RelatedBook``) shape.
    """
    page_stmt = (
        base.options(selectinload(BookORM.author))
        .order_by(BookORM.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    books = list((await session.scalars(page_stmt)).all())

    count_stmt = select(func.count()).select_from(base.subquery())
    total = await session.scalar(count_stmt) or 0

    return books, int(total)


async def list_popular_atmosphere_tags(
    session: AsyncSession,
    *,
    limit: int = 50,
) -> list[tuple[str, int]]:
    """Aggregate atmosphere tags over published books (plan §14.3).

    ``unnest(atmosphere_tags)`` over published books, GROUP BY tag,
    COUNT, ORDER BY count DESC then name ASC, LIMIT 50. Returns a list of
    ``(name, count)`` tuples; the route maps these to
    ``AtmosphereTagEntry``.
    """
    tag = func.unnest(BookORM.atmosphere_tags).label("tag")
    subq = select(tag).where(BookORM.published.is_(True)).subquery()

    count = func.count().label("count")
    stmt = (
        select(subq.c.tag, count)
        .group_by(subq.c.tag)
        .order_by(count.desc(), subq.c.tag.asc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [(row[0], int(row[1])) for row in rows]
