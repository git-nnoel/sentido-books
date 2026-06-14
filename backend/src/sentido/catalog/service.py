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

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sentido.catalog.logic import slug_with_disambiguator, slugify
from sentido.catalog.models import AuthorORM, BookORM, EditionORM
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
