"""Health endpoint smoke test.

Exercises the full FastAPI app surface — including the lifespan
handler, which builds the engine / sessionmaker / httpx client /
OpenAI client. None of those make network calls at construction time,
so this test does not need a live DB or OpenAI key (the dummy values
set in :mod:`tests.conftest` are enough).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from sentido.main import create_app


def test_health_returns_ok_payload() -> None:
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "1.0.0"}
