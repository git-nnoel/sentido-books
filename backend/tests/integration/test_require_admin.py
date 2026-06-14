"""Tests for the ``require_admin`` FastAPI dependency.

Builds a minimal app exposing a single guarded route and exercises the
four documented cases (plan §5.2): missing header, wrong scheme, wrong
token, correct token. No real DB or HTTP/OpenAI client is constructed
here because we mount the dependency on a bare ``FastAPI()`` instance
(no Sentido lifespan).

The error handler from :mod:`sentido.shared.errors` is registered so
the 401 response body matches the contract
(``{"detail": "unauthorized"}``).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from sentido.shared.auth import require_admin
from sentido.shared.config import get_settings
from sentido.shared.errors import register_exception_handlers

TEST_ADMIN_TOKEN = "test-admin-token-xyz"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A TestClient over a minimal app that mounts ``require_admin``."""
    monkeypatch.setenv("ADMIN_TOKEN", TEST_ADMIN_TOKEN)
    get_settings.cache_clear()

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/protected", dependencies=[Depends(require_admin)])
    async def protected() -> dict[str, str]:
        return {"ok": "true"}

    with TestClient(app) as tc:
        yield tc

    # Reset the settings cache so other tests aren't poisoned by the
    # overridden ADMIN_TOKEN.
    get_settings.cache_clear()


def test_missing_authorization_header_returns_401(client: TestClient) -> None:
    response = client.get("/protected")
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_wrong_scheme_returns_401(client: TestClient) -> None:
    response = client.get("/protected", headers={"Authorization": "Basic xyz"})
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_wrong_token_returns_401(client: TestClient) -> None:
    response = client.get(
        "/protected", headers={"Authorization": "Bearer wrongtoken"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_correct_token_returns_200(client: TestClient) -> None:
    response = client.get(
        "/protected", headers={"Authorization": f"Bearer {TEST_ADMIN_TOKEN}"}
    )
    assert response.status_code == 200
    assert response.json() == {"ok": "true"}
