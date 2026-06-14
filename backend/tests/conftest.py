"""Test environment bootstrap.

Sets required env vars before any ``sentido.*`` module is imported so
that :func:`sentido.shared.config.get_settings` (which is ``lru_cache``-
backed and validates required fields at construction) can succeed.

Tests that need different ADMIN_TOKEN / CORS_ORIGINS values
``monkeypatch.setenv`` and then clear the cache by calling
``get_settings.cache_clear()`` — see ``test_require_admin.py``.
"""

from __future__ import annotations

import os

# Plan §8: minimum required env. Values are dummies; tests that hit a
# real DB / OpenAI must override these explicitly.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://sentido:sentido@localhost:5433/sentido_test",
)
os.environ.setdefault("OPENAI_API_KEY", "sk-test-key")
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
os.environ.setdefault("GOOGLE_BOOKS_API_KEY", "test-google-books-key")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
