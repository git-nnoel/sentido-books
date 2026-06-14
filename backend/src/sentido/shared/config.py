"""Application settings — the **single** source of env loading.

All configuration is read from environment variables (`.env` in dev,
real env in prod) per the backend implementation plan §8 and
backend-system-architecture skill R1–R3. No other module in the
service may import `os.environ` or `os.getenv`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables.

    Variable names mirror plan §8 exactly. Required vars without defaults
    will fail validation at startup (skill R6 — misconfiguration must
    fail at startup, not at first request).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Required ---
    DATABASE_URL: str = Field(
        ...,
        description="SQLAlchemy async URL, e.g. postgresql+asyncpg://user:pw@host:5432/db",
    )
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key for LLM + embeddings.")
    ADMIN_TOKEN: str = Field(..., description="Static bearer token for admin endpoints.")
    GOOGLE_BOOKS_API_KEY: str = Field(..., description="Google Books API key (free tier).")
    CORS_ORIGINS: str = Field(
        ...,
        description="Comma-separated list of allowed origins for CORS.",
    )

    # --- Optional with defaults ---
    OPENAI_BASE_URL: str = Field(
        default="https://api.openai.com/v1",
        description="Override for OpenAI base URL (proxy / mocking in tests).",
    )
    OPEN_LIBRARY_USER_AGENT: str = Field(
        default="Sentido/1.0",
        description="User-Agent header sent to Open Library (mandatory by their policy).",
    )
    LOG_LEVEL: str = Field(default="INFO")
    ENV: Literal["development", "production"] = Field(default="development")

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _cors_origins_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("CORS_ORIGINS must contain at least one origin")
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Parsed CORS_ORIGINS as a clean list of origins."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings singleton.

    Constructed once per process. FastAPI lifespan should call this at
    startup so misconfiguration is caught before the app starts serving.
    """
    return Settings()  # type: ignore[call-arg]
