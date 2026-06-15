"""Search pure helpers — query normalization, cache key, distance math.

Plan §3.2 / skill §3.2: no I/O lives here. These functions are
deterministic data → data transforms used by ``search.service`` and
tested directly without mocks (plan §12).

Three concerns:

* :func:`normalize_query` — strip + collapse internal whitespace so
  trivial duplicates ("  solidão " vs "solidão") share a cache entry.
* :func:`cache_key` — produce the 64-char hex digest stored as
  ``resonance_cache.query_hash`` (plan §6 / models.py).
* :func:`cosine_similarity_from_distance` — convert pgvector's cosine
  *distance* (0..2) into the cosine *similarity* (1..-1) returned in
  the API contract (plan §5.1).
"""

from __future__ import annotations

import hashlib
import re
import uuid

__all__ = [
    "cache_key",
    "cosine_similarity_from_distance",
    "normalize_query",
]

# Internal whitespace runs are collapsed to a single space. ``\s+`` is
# Unicode-aware in Python's ``re`` module which is what we want — the
# PT-BR query stream contains non-breaking spaces and similar
# whitespace variants in practice.
_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_query(raw: str) -> str:
    """Return ``raw`` with leading/trailing whitespace stripped and
    internal whitespace runs collapsed to a single space.

    Pure. Used to avoid trivial cache duplicates and to feed a stable
    string to both the embedding call and :func:`cache_key`.
    """
    return _WHITESPACE_RUN.sub(" ", raw).strip()


def cache_key(query: str, book_id: uuid.UUID) -> str:
    """Compute the resonance cache key for a ``(query, book_id)`` pair.

    Returns the SHA-256 hex digest of ``f"{query}|{book_id}"`` encoded
    as UTF-8 — 64 hex chars, matching the ``query_hash CHAR(64)``
    column declared in :mod:`sentido.search.models`. The pipe
    separator prevents ambiguity between adjacent strings (e.g.
    "foo" + "bar"  vs  "foob" + "ar").

    Pure, deterministic. The exact same composition must be used on
    both the read and the write side of the cache — both call sites
    in ``search.service.semantic_search`` route through this helper.
    """
    payload = f"{query}|{book_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def cosine_similarity_from_distance(distance: float) -> float:
    """Convert pgvector's cosine *distance* into cosine *similarity*.

    pgvector returns 0 for identical vectors and 2 for opposite ones.
    The API contract (plan §5.1) returns similarity: 1 = identical,
    -1 = opposite. The two are related by ``similarity = 1 - distance``.

    Pure.
    """
    return 1.0 - distance
