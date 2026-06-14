"""Ingestion DTOs — both the request body and the internal normalized
shape produced by :mod:`sentido.ingestion.logic`.

These types are internal to the ingestion module's contract. Only
:class:`IngestRequest` is exposed via the admin route (re-exported from
:mod:`sentido.admin.schemas`). :class:`NormalizedBook` and
:class:`NormalizedAuthor` are the cross-source domain shape that
``catalog.service.create_book_from_normalized`` consumes — keeping
ingestion's external-API quirks out of the catalog write path.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class IngestRequest(BaseModel):
    """Body of ``POST /v1/admin/books/ingest`` (plan §5.2).

    Carries only the raw ISBN string — normalization and validation
    happen inside :func:`sentido.ingestion.logic.normalize_isbn` so the
    same code path enforces format on every entry point (admin route,
    future batch importer). The route handler raises ``ValueError`` on
    invalid input; the global exception handler translates that to
    HTTP 400 with ``{"detail": "<message>"}`` per skill R8.
    """

    model_config = ConfigDict(extra="forbid")

    isbn: str


class NormalizedAuthor(BaseModel):
    """An author extracted from an external response.

    ``ol_author_id`` is the Open Library key (e.g. ``"/authors/OL2A"``)
    when present — used for upsert-by-id in
    ``catalog.service.find_or_create_author``. When unavailable we fall
    back to case-insensitive name match.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    ol_author_id: str | None = None


class NormalizedBook(BaseModel):
    """Cross-source normalized book shape consumed by
    :func:`sentido.catalog.service.create_book_from_normalized`.

    Anything an external API gives us that doesn't fit here is dropped
    at the normalizer boundary (``logic.normalize_open_library_response``)
    — the catalog layer never sees vendor-shaped data.
    """

    model_config = ConfigDict(extra="forbid")

    isbn: str
    title: str
    authors: list[NormalizedAuthor]
    publishers: list[str]
    publish_year: int | None = None
    cover_url: str | None = None
    ol_work_id: str | None = None
