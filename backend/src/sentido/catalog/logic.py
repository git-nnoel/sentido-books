"""Catalog pure functions — slug generation and disambiguator helpers.

Functional core (skill §3.2 / plan §3.2). No I/O, no DB, no httpx. These
helpers take strings and return strings. They are called from
``catalog.service`` when persisting authors/books and from anywhere that
needs deterministic slug derivation.

Slug strategy mirrors plan §4.3:

- ASCII-fold (NFKD + drop combining marks)
- lowercase
- collapse any non-alphanumeric run into a single hyphen
- strip leading/trailing hyphens

Collisions are resolved by callers in ``service.py`` (the rule lives
there because resolving a collision requires a DB lookup). This module
provides the *building blocks* — :func:`slugify` and
:func:`slug_with_disambiguator` — that the service uses to try
candidate slugs in order.
"""

from __future__ import annotations

import re
import unicodedata


def slugify(text: str) -> str:
    """Return an ASCII, lowercased, hyphen-separated slug.

    Steps:
        1. NFKD-normalize so accented characters split into base + combining marks.
        2. Drop the combining marks (``unicodedata.combining(c)``).
        3. Lowercase.
        4. Replace any run of non-alphanumeric characters with a single ``-``.
        5. Strip leading/trailing hyphens.

    The result contains only ``[a-z0-9-]``. An empty or whitespace-only
    input returns the empty string — callers (the service) are
    responsible for treating that as invalid input.

    Examples:
        >>> slugify("O Estrangeiro")
        'o-estrangeiro'
        >>> slugify("A Vegetariana")
        'a-vegetariana'
        >>> slugify("L'Étranger")
        'l-etranger'
        >>> slugify("  ")
        ''
    """
    if not text:
        return ""

    # 1–2: ASCII-fold via NFKD + drop combining marks.
    normalized = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(c for c in normalized if not unicodedata.combining(c))

    # 3: lowercase.
    lowered = ascii_only.lower()

    # 4: collapse non-alphanumeric runs into single hyphens. ``\W`` would
    # also match underscores, which is fine to collapse — but we use an
    # explicit class to be precise about what counts as a separator.
    hyphenated = re.sub(r"[^a-z0-9]+", "-", lowered)

    # 5: strip leading/trailing hyphens.
    return hyphenated.strip("-")


def slug_with_disambiguator(base: str, suffix: str) -> str:
    """Append ``-{slugify(suffix)}`` to a base slug for collision resolution.

    Used by the catalog service when a base slug (e.g. ``slugify(title)``)
    is already taken. The suffix is typically the author's last name or a
    numeric counter; it is itself slugified so callers can pass raw user
    strings safely.

    If ``suffix`` slugifies to the empty string, the base is returned
    unchanged. If ``base`` is empty, the slugified suffix is returned on
    its own.

    Examples:
        >>> slug_with_disambiguator("o-estrangeiro", "Camus")
        'o-estrangeiro-camus'
        >>> slug_with_disambiguator("foo", "  ")
        'foo'
        >>> slug_with_disambiguator("", "Camus")
        'camus'
    """
    suffix_slug = slugify(suffix)
    if not suffix_slug:
        return base
    if not base:
        return suffix_slug
    return f"{base}-{suffix_slug}"
