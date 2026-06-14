"""Ingestion pure functions — ISBN normalization + Open Library response
parsing.

Functional core (plan §3.2, skill §3.2). No I/O — these functions take
strings/dicts and return strings/Pydantic models. They are exercised
directly in unit tests without fixtures or mocks (skill R15 Mode B).

Open Library's ``api/books?...&jscmd=data`` response is loosely typed:
fields are often optional, sometimes wrapped in lists, sometimes
absent entirely. The parser is intentionally defensive (``.get()``
everywhere) and returns ``None`` when the core requirement — a title
plus at least one author — is missing. The service translates
``None`` into a 404 (plan §5.2).
"""

from __future__ import annotations

import re
from typing import Any

from sentido.ingestion.schemas import NormalizedAuthor, NormalizedBook

# Open Library publish_date examples observed in the wild:
#   "1942", "Sep 1942", "September 1942", "1942-09-01", "Sept. 1, 1942"
# We pull the first 4-digit run and treat it as the year. Anything else
# is ignored — we'd rather lose a year than crash on a weird format.
_YEAR_RE = re.compile(r"\b(\d{4})\b")


def normalize_isbn(raw: str) -> str:
    """Return a normalized ISBN of length 10 or 13.

    Strips dashes/whitespace and uppercases any final ``x`` to ``X``
    (the ISBN-10 checkdigit). ISBN-13 must be 13 digits. ISBN-10 may
    end in ``X`` (kept in the stored form so the checkdigit survives
    round-trip).

    Raises ``ValueError`` on any input that does not normalize to a
    valid ISBN-10 or ISBN-13. The exception handler in
    :mod:`sentido.shared.errors` translates this into a 400 response.
    """
    if raw is None:
        raise ValueError("isbn is required")

    # Uppercase so 'x' is treated like 'X' (ISBN-10 checkdigit).
    upper = raw.upper()

    # Strip everything that is not a digit or X.
    cleaned = re.sub(r"[^0-9X]", "", upper)

    # If an X is present it must be the *only* X and must be the last
    # character — the ISBN-10 checkdigit. Anywhere else is invalid.
    if "X" in cleaned and (cleaned.count("X") > 1 or not cleaned.endswith("X")):
        raise ValueError("invalid isbn: X may only appear as the final checkdigit")

    if len(cleaned) not in (10, 13):
        raise ValueError("isbn must be 10 or 13 characters after normalization")

    if len(cleaned) == 13 and not cleaned.isdigit():
        raise ValueError("isbn-13 must be all digits")

    if len(cleaned) == 10:
        head, tail = cleaned[:9], cleaned[9]
        if not head.isdigit() or tail not in "0123456789X":
            raise ValueError("invalid isbn-10")

    return cleaned


def _first_year(text: str | None) -> int | None:
    """Pull the first 4-digit year out of a free-form date string."""
    if not text:
        return None
    m = _YEAR_RE.search(text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:  # pragma: no cover — regex guarantees digits.
        return None


def _extract_cover_url(payload: dict[str, Any]) -> str | None:
    """Prefer the ``large`` cover, fall back to ``medium`` then ``small``."""
    cover = payload.get("cover") or {}
    if not isinstance(cover, dict):
        return None
    for key in ("large", "medium", "small"):
        url = cover.get(key)
        if isinstance(url, str) and url:
            return url
    return None


def _extract_authors(payload: dict[str, Any]) -> list[NormalizedAuthor]:
    """Pull the authors list out of the Open Library payload.

    Open Library represents authors as a list of dicts with at least
    ``name``, and often ``url`` (e.g. ``https://openlibrary.org/authors/OL2A/...``)
    or ``key`` (``/authors/OL2A``). We try to extract an OL author id
    from either form.
    """
    raw_authors = payload.get("authors") or []
    if not isinstance(raw_authors, list):
        return []

    result: list[NormalizedAuthor] = []
    for entry in raw_authors:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        ol_id: str | None = None
        key = entry.get("key")
        if isinstance(key, str) and key.startswith("/authors/"):
            ol_id = key
        else:
            url = entry.get("url")
            if isinstance(url, str):
                m = re.search(r"/authors/(OL\w+)", url)
                if m:
                    ol_id = f"/authors/{m.group(1)}"
        result.append(NormalizedAuthor(name=name.strip(), ol_author_id=ol_id))
    return result


def _extract_publishers(payload: dict[str, Any]) -> list[str]:
    raw = payload.get("publishers") or []
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for entry in raw:
        if isinstance(entry, dict):
            name = entry.get("name")
            if isinstance(name, str) and name.strip():
                out.append(name.strip())
        elif isinstance(entry, str) and entry.strip():
            out.append(entry.strip())
    return out


def _extract_ol_work_id(payload: dict[str, Any]) -> str | None:
    works = payload.get("works") or []
    if not isinstance(works, list) or not works:
        return None
    first = works[0]
    if not isinstance(first, dict):
        return None
    key = first.get("key")
    if isinstance(key, str) and key.startswith("/works/"):
        return key
    return None


def normalize_open_library_response(
    payload: dict[str, Any], isbn: str
) -> NormalizedBook | None:
    """Project an Open Library ``jscmd=data`` book dict into our internal shape.

    Returns ``None`` when the payload is empty, or when the response
    lacks both a title and at least one usable author — those are the
    minimum fields the catalog needs to create a row, so partial data
    is treated as "no result" (the service raises 404).
    """
    if not isinstance(payload, dict) or not payload:
        return None

    title = payload.get("title")
    if not isinstance(title, str) or not title.strip():
        return None

    authors = _extract_authors(payload)
    if not authors:
        return None

    return NormalizedBook(
        isbn=isbn,
        title=title.strip(),
        authors=authors,
        publishers=_extract_publishers(payload),
        publish_year=_first_year(payload.get("publish_date")),
        cover_url=_extract_cover_url(payload),
        ol_work_id=_extract_ol_work_id(payload),
    )
