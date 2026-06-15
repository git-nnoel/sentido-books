"""Unit tests for ``search.logic`` — pure helpers, no fixtures, no mocks.

Plan §12 / skill R15: pure functions exercised directly.
"""

from __future__ import annotations

import uuid

import pytest

from sentido.search.logic import (
    cache_key,
    cosine_similarity_from_distance,
    normalize_query,
)


class TestCacheKey:
    def test_is_deterministic_and_64_hex(self) -> None:
        book_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        a = cache_key("solidão", book_id)
        b = cache_key("solidão", book_id)
        assert a == b
        assert len(a) == 64
        assert all(c in "0123456789abcdef" for c in a)

    def test_changes_when_query_changes(self) -> None:
        book_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        assert cache_key("foo", book_id) != cache_key("bar", book_id)

    def test_changes_when_book_id_changes(self) -> None:
        a = uuid.UUID("11111111-1111-1111-1111-111111111111")
        b = uuid.UUID("22222222-2222-2222-2222-222222222222")
        assert cache_key("same query", a) != cache_key("same query", b)

    def test_separator_prevents_adjacent_collision(self) -> None:
        """The pipe separator means "foo|<id>" cannot collide with
        "foob|<id>" — the boundary is unambiguous."""
        book_id = uuid.UUID("33333333-3333-3333-3333-333333333333")
        assert cache_key("foo", book_id) != cache_key("foob", book_id)


class TestNormalizeQuery:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("  solidão  ", "solidão"),
            ("solidão", "solidão"),
            ("solidão   que   não   dói", "solidão que não dói"),
            ("\tsolidão\n", "solidão"),
            ("multi\nline\nquery", "multi line query"),
            ("", ""),
        ],
    )
    def test_strip_and_collapse(self, raw: str, expected: str) -> None:
        assert normalize_query(raw) == expected


class TestCosineSimilarityFromDistance:
    @pytest.mark.parametrize(
        ("distance", "expected"),
        [
            (0.0, 1.0),
            (2.0, -1.0),
            (1.0, 0.0),
            (0.5, 0.5),
        ],
    )
    def test_conversion(self, distance: float, expected: float) -> None:
        assert cosine_similarity_from_distance(distance) == pytest.approx(expected)
