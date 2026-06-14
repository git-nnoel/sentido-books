"""Unit tests for ``catalog.logic`` — pure slug helpers.

These tests follow the skill R15 (Mode B) rule: pure functions are
exercised directly without fixtures or mocks. Plan §4.3 is the
behavioural spec.
"""

from __future__ import annotations

import pytest

from sentido.catalog.logic import slug_with_disambiguator, slugify


class TestSlugify:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("O Estrangeiro", "o-estrangeiro"),
            ("A Vegetariana", "a-vegetariana"),
            ("L'Étranger", "l-etranger"),
            ("Crime e Castigo", "crime-e-castigo"),
            ("Norwegian Wood", "norwegian-wood"),
            ("Cem Anos de Solidão", "cem-anos-de-solidao"),
            # Multiple accents collapse cleanly.
            ("São Paulo: a cidade", "sao-paulo-a-cidade"),
            # Already-clean slugs round-trip.
            ("already-clean", "already-clean"),
            # Numbers are preserved.
            ("1984", "1984"),
            ("2666", "2666"),
        ],
    )
    def test_basic_cases(self, text: str, expected: str) -> None:
        assert slugify(text) == expected

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("", ""),
            ("   ", ""),
            ("---", ""),
            ("!!!", ""),
            ("   :   ", ""),
        ],
    )
    def test_empty_or_punctuation_only_returns_empty(
        self, text: str, expected: str
    ) -> None:
        assert slugify(text) == expected

    def test_collapses_runs_of_punctuation(self) -> None:
        assert slugify("foo   bar---baz") == "foo-bar-baz"
        assert slugify("foo: bar; baz!") == "foo-bar-baz"

    def test_strips_leading_and_trailing_hyphens(self) -> None:
        assert slugify("---foo---") == "foo"
        assert slugify("   foo   ") == "foo"

    def test_lowercases(self) -> None:
        assert slugify("UPPER") == "upper"
        assert slugify("MixedCase") == "mixedcase"

    def test_handles_combining_marks_explicitly(self) -> None:
        # Compose vs decompose forms both yield the same slug.
        assert slugify("Étranger") == "etranger"
        # NFKD form (explicit combining mark)
        assert slugify("Étranger") == "etranger"


class TestSlugWithDisambiguator:
    def test_appends_slugified_suffix(self) -> None:
        assert slug_with_disambiguator("o-estrangeiro", "Camus") == "o-estrangeiro-camus"

    def test_suffix_is_slugified(self) -> None:
        assert slug_with_disambiguator("foo", "L'Étranger") == "foo-l-etranger"

    def test_numeric_suffix(self) -> None:
        assert slug_with_disambiguator("foo", "2") == "foo-2"
        assert slug_with_disambiguator("foo", "10") == "foo-10"

    def test_empty_suffix_returns_base_unchanged(self) -> None:
        assert slug_with_disambiguator("foo", "") == "foo"
        assert slug_with_disambiguator("foo", "   ") == "foo"
        assert slug_with_disambiguator("foo", "!!!") == "foo"

    def test_empty_base_returns_suffix_slug(self) -> None:
        assert slug_with_disambiguator("", "Camus") == "camus"

    def test_both_empty_returns_empty(self) -> None:
        assert slug_with_disambiguator("", "") == ""
