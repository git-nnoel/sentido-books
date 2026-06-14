"""Unit tests for ``ingestion.logic`` — ISBN normalization + Open
Library response parsing.

Skill R15 (Mode B): pure functions tested directly without mocks.
"""

from __future__ import annotations

import pytest

from sentido.ingestion.logic import (
    normalize_isbn,
    normalize_open_library_response,
)
from sentido.ingestion.schemas import NormalizedBook


class TestNormalizeIsbn:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("9788501062451", "9788501062451"),
            ("978-85-01-06245-1", "9788501062451"),
            ("978 85 01 06245 1", "9788501062451"),
            ("  9788501062451  ", "9788501062451"),
            ("0140449132", "0140449132"),
            # ISBN-10 with X checkdigit.
            ("020161622X", "020161622X"),
            ("0-201-61622-x", "020161622X"),
        ],
    )
    def test_valid_inputs(self, raw: str, expected: str) -> None:
        assert normalize_isbn(raw) == expected

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "12345",
            "12345678901234",  # 14 digits
            "abcdefghij",
            "978850106245",  # 12 digits
            "X9788501062451",  # X not at end
            "97885010624XX",  # two Xs
            "020X61622X",  # X in middle of ISBN-10
        ],
    )
    def test_rejects_invalid(self, raw: str) -> None:
        with pytest.raises(ValueError):
            normalize_isbn(raw)

    def test_rejects_none(self) -> None:
        with pytest.raises(ValueError):
            normalize_isbn(None)  # type: ignore[arg-type]


# A minimal but realistic shape of Open Library's
# /api/books?bibkeys=ISBN:...&jscmd=data inner record. Real responses
# carry more fields; the parser is defensive against missing ones.
_FULL_PAYLOAD = {
    "url": "https://openlibrary.org/books/OL1234M/Foo",
    "key": "/books/OL1234M",
    "title": "O Estrangeiro",
    "authors": [
        {
            "url": "https://openlibrary.org/authors/OL2A/Albert_Camus",
            "name": "Albert Camus",
        }
    ],
    "publishers": [{"name": "Record"}],
    "publish_date": "Sep 14, 2014",
    "cover": {
        "large": "https://covers.openlibrary.org/b/id/12345-L.jpg",
        "medium": "https://covers.openlibrary.org/b/id/12345-M.jpg",
        "small": "https://covers.openlibrary.org/b/id/12345-S.jpg",
    },
    "works": [{"key": "/works/OL1W"}],
}


class TestNormalizeOpenLibraryResponse:
    def test_happy_path(self) -> None:
        result = normalize_open_library_response(_FULL_PAYLOAD, "9788501062451")
        assert isinstance(result, NormalizedBook)
        assert result.isbn == "9788501062451"
        assert result.title == "O Estrangeiro"
        assert len(result.authors) == 1
        assert result.authors[0].name == "Albert Camus"
        assert result.authors[0].ol_author_id == "/authors/OL2A"
        assert result.publishers == ["Record"]
        assert result.publish_year == 2014
        assert result.cover_url == "https://covers.openlibrary.org/b/id/12345-L.jpg"
        assert result.ol_work_id == "/works/OL1W"

    def test_falls_back_to_medium_cover(self) -> None:
        payload = {**_FULL_PAYLOAD, "cover": {"medium": "med.jpg", "small": "small.jpg"}}
        result = normalize_open_library_response(payload, "9788501062451")
        assert result is not None
        assert result.cover_url == "med.jpg"

    def test_missing_title_returns_none(self) -> None:
        payload = {k: v for k, v in _FULL_PAYLOAD.items() if k != "title"}
        assert normalize_open_library_response(payload, "9788501062451") is None

    def test_blank_title_returns_none(self) -> None:
        payload = {**_FULL_PAYLOAD, "title": "   "}
        assert normalize_open_library_response(payload, "9788501062451") is None

    def test_missing_authors_returns_none(self) -> None:
        payload = {k: v for k, v in _FULL_PAYLOAD.items() if k != "authors"}
        assert normalize_open_library_response(payload, "9788501062451") is None

    def test_authors_without_name_returns_none(self) -> None:
        payload = {**_FULL_PAYLOAD, "authors": [{"url": "/authors/OL2A"}]}
        assert normalize_open_library_response(payload, "9788501062451") is None

    def test_empty_payload_returns_none(self) -> None:
        assert normalize_open_library_response({}, "9788501062451") is None

    def test_non_dict_payload_returns_none(self) -> None:
        assert normalize_open_library_response(None, "9788501062451") is None  # type: ignore[arg-type]
        assert normalize_open_library_response([], "9788501062451") is None  # type: ignore[arg-type]

    def test_missing_optional_fields(self) -> None:
        payload = {
            "title": "Minimal",
            "authors": [{"name": "Some Author"}],
        }
        result = normalize_open_library_response(payload, "1234567890")
        assert result is not None
        assert result.title == "Minimal"
        assert result.publishers == []
        assert result.publish_year is None
        assert result.cover_url is None
        assert result.ol_work_id is None
        assert result.authors[0].ol_author_id is None

    def test_publish_date_year_extraction(self) -> None:
        for raw, expected in [
            ("1942", 1942),
            ("September 1942", 1942),
            ("Sep 14, 2014", 2014),
            ("2014-09-14", 2014),
        ]:
            payload = {**_FULL_PAYLOAD, "publish_date": raw}
            result = normalize_open_library_response(payload, "9788501062451")
            assert result is not None
            assert result.publish_year == expected, f"failed for {raw!r}"

    def test_publish_date_without_year_yields_none(self) -> None:
        payload = {**_FULL_PAYLOAD, "publish_date": "no year here"}
        result = normalize_open_library_response(payload, "9788501062451")
        assert result is not None
        assert result.publish_year is None

    def test_author_key_form_extracted(self) -> None:
        payload = {
            **_FULL_PAYLOAD,
            "authors": [{"name": "A", "key": "/authors/OL5A"}],
        }
        result = normalize_open_library_response(payload, "9788501062451")
        assert result is not None
        assert result.authors[0].ol_author_id == "/authors/OL5A"

    def test_publishers_as_plain_strings(self) -> None:
        payload = {**_FULL_PAYLOAD, "publishers": ["Penguin", "Vintage"]}
        result = normalize_open_library_response(payload, "9788501062451")
        assert result is not None
        assert result.publishers == ["Penguin", "Vintage"]
