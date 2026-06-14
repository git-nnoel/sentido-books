"""Unit tests for ``generation.logic`` — pure helpers.

Plan §12 / skill R15 (Mode B): functions in ``logic.py`` are exercised
directly with no fixtures or mocks. Each test names a single rule
from plan §11 D2 (embedding text composition) or plan §4.2 (profile
JSON shape).
"""

from __future__ import annotations

import json

import pytest

from sentido.generation.logic import (
    clean_atmosphere_tags,
    compose_embedding_text,
    parse_profile,
)

# ---------------------------------------------------------------------------
# parse_profile
# ---------------------------------------------------------------------------


def _valid_payload() -> dict:
    return {
        "anguish": 6.0,
        "melancholy": 4.0,
        "hope": 1.0,
        "violence": 5.0,
        "tenderness": 1.0,
        "strangeness": 8.5,
        "atmosphere_tags": ["apatia", "absurdo", "sol como violência"],
        "narrative_pace": "progressive",
    }


class TestParseProfileValid:
    def test_round_trip(self) -> None:
        result = parse_profile(json.dumps(_valid_payload()))
        assert result.profile.anguish == 6.0
        assert result.profile.melancholy == 4.0
        assert result.profile.hope == 1.0
        assert result.profile.violence == 5.0
        assert result.profile.tenderness == 1.0
        assert result.profile.strangeness == 8.5
        assert result.atmosphere_tags == ["apatia", "absurdo", "sol como violência"]
        assert result.narrative_pace == "progressive"

    def test_extra_top_level_keys_ignored(self) -> None:
        payload = _valid_payload()
        payload["rationale"] = "should be ignored"
        result = parse_profile(json.dumps(payload))
        assert result.narrative_pace == "progressive"

    def test_tags_cleaned_during_parse(self) -> None:
        # Mixed-case and whitespace get normalized by the cleaner before
        # validation, so a payload with uppercase tags still parses.
        payload = _valid_payload()
        payload["atmosphere_tags"] = ["  Apatia  ", "ABSURDO", "sol como violência"]
        result = parse_profile(json.dumps(payload))
        assert result.atmosphere_tags == ["apatia", "absurdo", "sol como violência"]


class TestParseProfileInvalid:
    def test_malformed_json(self) -> None:
        with pytest.raises(ValueError, match="profile json invalid"):
            parse_profile("not json")

    def test_top_level_not_object(self) -> None:
        with pytest.raises(ValueError, match="must be an object"):
            parse_profile("[1, 2, 3]")

    def test_missing_axis(self) -> None:
        payload = _valid_payload()
        del payload["hope"]
        with pytest.raises(ValueError, match="hope"):
            parse_profile(json.dumps(payload))

    def test_out_of_range_high(self) -> None:
        payload = _valid_payload()
        payload["anguish"] = 11.0
        with pytest.raises(ValueError, match="anguish"):
            parse_profile(json.dumps(payload))

    def test_out_of_range_low(self) -> None:
        payload = _valid_payload()
        payload["violence"] = -1.0
        with pytest.raises(ValueError, match="violence"):
            parse_profile(json.dumps(payload))

    def test_wrong_narrative_pace_literal(self) -> None:
        payload = _valid_payload()
        payload["narrative_pace"] = "medium"
        with pytest.raises(ValueError, match="narrative_pace"):
            parse_profile(json.dumps(payload))

    def test_atmosphere_tags_not_a_list(self) -> None:
        payload = _valid_payload()
        payload["atmosphere_tags"] = "apatia, absurdo"
        with pytest.raises(ValueError, match="atmosphere_tags"):
            parse_profile(json.dumps(payload))

    def test_too_few_tags(self) -> None:
        payload = _valid_payload()
        payload["atmosphere_tags"] = ["apatia"]
        with pytest.raises(ValueError, match="atmosphere_tags"):
            parse_profile(json.dumps(payload))


# ---------------------------------------------------------------------------
# compose_embedding_text
# ---------------------------------------------------------------------------


class TestComposeEmbeddingText:
    def test_exact_string_match(self) -> None:
        out = compose_embedding_text(
            title="O Estrangeiro",
            author_name="Albert Camus",
            synopsis="Meursault não chora no funeral da mãe.",
            atmosphere_tags=["apatia", "absurdo", "sol como violência"],
            narrative_pace="progressive",
        )
        expected = (
            "O Estrangeiro — Albert Camus. Meursault não chora no funeral da mãe.\n"
            "Atmosfera: apatia, absurdo, sol como violência.\n"
            "Ritmo: progressive."
        )
        assert out == expected

    def test_deterministic(self) -> None:
        kwargs = {
            "title": "Norwegian Wood",
            "author_name": "Haruki Murakami",
            "synopsis": "Toru recorda Naoko.",
            "atmosphere_tags": ["nostalgia", "chuva", "silêncio que sufoca"],
            "narrative_pace": "slow",
        }
        first = compose_embedding_text(**kwargs)
        second = compose_embedding_text(**kwargs)
        assert first == second

    def test_empty_tags_join_to_empty_string(self) -> None:
        # Embedding text composition does not enforce tag bounds — that's
        # the profile schema's job. Composition stays a pure formatter.
        out = compose_embedding_text(
            title="Book",
            author_name="Author",
            synopsis="Synopsis.",
            atmosphere_tags=[],
            narrative_pace="slow",
        )
        assert "Atmosfera: .\n" in out


# ---------------------------------------------------------------------------
# clean_atmosphere_tags
# ---------------------------------------------------------------------------


class TestCleanAtmosphereTags:
    def test_strip_and_lowercase(self) -> None:
        assert clean_atmosphere_tags(["  Apatia ", "ABSURDO", "Sol Como Violência"]) == [
            "apatia",
            "absurdo",
            "sol como violência",
        ]

    def test_drops_empty_entries(self) -> None:
        assert clean_atmosphere_tags(["apatia", "", "   ", "absurdo"]) == [
            "apatia",
            "absurdo",
        ]

    def test_caps_to_five(self) -> None:
        tags = [f"tag{i}" for i in range(10)]
        result = clean_atmosphere_tags(tags)
        assert len(result) == 5
        assert result == ["tag0", "tag1", "tag2", "tag3", "tag4"]

    def test_passthrough_when_already_clean(self) -> None:
        tags = ["apatia", "absurdo", "sol como violência"]
        assert clean_atmosphere_tags(tags) == tags
