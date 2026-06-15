"""Integration tests for dimension navigation (B7 / plan §14.3).

Covers one happy path per ``GET /v1/explore`` mode (tag, emotion, pace),
the ``GET /v1/explore/tags`` aggregation, and the 400 validation paths
(missing required param; invalid mode handled by FastAPI's Literal →
422). Public endpoints, no auth; route → catalog service → Postgres.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sentido.catalog.models import AuthorORM, BookORM
from sentido.main import create_app
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


@pytest.fixture
def client(test_engine: AsyncEngine) -> Iterator[TestClient]:
    app = create_app()
    with TestClient(app) as tc:
        app.state.sessionmaker = async_sessionmaker(
            test_engine, expire_on_commit=False
        )
        yield tc


def _profile(**axes: float) -> dict[str, float]:
    base = {
        "anguish": 0.0,
        "melancholy": 0.0,
        "hope": 0.0,
        "violence": 0.0,
        "tenderness": 0.0,
        "strangeness": 0.0,
    }
    base.update(axes)
    return base


async def _seed(test_session) -> None:
    author = AuthorORM(slug="albert-camus", name="Albert Camus")
    test_session.add(author)
    await test_session.flush()

    base = dt.datetime(2026, 6, 1, 12, 0, tzinfo=dt.UTC)

    test_session.add_all(
        [
            # published, tag=apatia, pace=slow, anguish=8.0
            BookORM(
                slug="o-estrangeiro",
                title="O Estrangeiro",
                author_id=author.id,
                atmosphere_tags=["apatia", "absurdo"],
                narrative_pace="slow",
                emotional_profile=_profile(anguish=8.0),
                published=True,
                embedding_status="done",
                profile_status="approved",
                updated_at=base + dt.timedelta(hours=2),
            ),
            # published, tag=apatia, pace=frenetic, anguish=3.0
            BookORM(
                slug="a-nausea",
                title="A Náusea",
                author_id=author.id,
                atmosphere_tags=["apatia"],
                narrative_pace="frenetic",
                emotional_profile=_profile(anguish=3.0),
                published=True,
                embedding_status="done",
                profile_status="approved",
                updated_at=base + dt.timedelta(hours=1),
            ),
            # UNPUBLISHED — must never appear in explore results.
            BookORM(
                slug="rascunho",
                title="Rascunho",
                author_id=author.id,
                atmosphere_tags=["apatia"],
                narrative_pace="slow",
                emotional_profile=_profile(anguish=9.9),
                published=False,
                embedding_status="pending",
                profile_status="pending",
                updated_at=base + dt.timedelta(hours=3),
            ),
        ]
    )
    await test_session.commit()


class TestExploreModes:
    async def test_mode_tag(
        self,
        client: TestClient,
        test_session,
    ) -> None:
        await _seed(test_session)
        response = client.get(
            "/v1/explore", params={"mode": "tag", "value": "apatia"}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["mode"] == "tag"
        assert body["value"] == "apatia"
        assert body["total"] == 2
        # updated_at DESC — o-estrangeiro (newer) before a-nausea; draft absent.
        assert [r["slug"] for r in body["results"]] == ["o-estrangeiro", "a-nausea"]

    async def test_mode_emotion_orders_by_axis_desc(
        self,
        client: TestClient,
        test_session,
    ) -> None:
        await _seed(test_session)
        response = client.get(
            "/v1/explore",
            params={"mode": "emotion", "axis": "anguish", "min": 1.0},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["mode"] == "emotion"
        assert body["value"] == "anguish"
        # anguish DESC: 8.0 (o-estrangeiro) before 3.0 (a-nausea); draft absent.
        assert [r["slug"] for r in body["results"]] == ["o-estrangeiro", "a-nausea"]

    async def test_mode_emotion_min_filters(
        self,
        client: TestClient,
        test_session,
    ) -> None:
        await _seed(test_session)
        response = client.get(
            "/v1/explore",
            params={"mode": "emotion", "axis": "anguish", "min": 5.0},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert [r["slug"] for r in body["results"]] == ["o-estrangeiro"]

    async def test_mode_pace(
        self,
        client: TestClient,
        test_session,
    ) -> None:
        await _seed(test_session)
        response = client.get(
            "/v1/explore", params={"mode": "pace", "value": "slow"}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["mode"] == "pace"
        assert body["value"] == "slow"
        # Only the published slow book; the slow draft is excluded.
        assert [r["slug"] for r in body["results"]] == ["o-estrangeiro"]

    async def test_empty_results_is_200(
        self,
        client: TestClient,
        test_session,
    ) -> None:
        await _seed(test_session)
        response = client.get(
            "/v1/explore", params={"mode": "tag", "value": "inexistente"}
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["results"] == []
        assert body["total"] == 0


class TestExploreValidation:
    async def test_tag_missing_value_400(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/v1/explore", params={"mode": "tag"})
        assert response.status_code == 400, response.text
        assert response.json() == {"detail": "mode=tag requires a value"}

    async def test_emotion_missing_axis_400(
        self,
        client: TestClient,
    ) -> None:
        response = client.get("/v1/explore", params={"mode": "emotion"})
        assert response.status_code == 400, response.text
        assert response.json() == {"detail": "mode=emotion requires an axis"}

    async def test_emotion_unknown_axis_400(
        self,
        client: TestClient,
    ) -> None:
        response = client.get(
            "/v1/explore", params={"mode": "emotion", "axis": "joy"}
        )
        assert response.status_code == 400, response.text

    async def test_invalid_mode_422(
        self,
        client: TestClient,
    ) -> None:
        # ``mode`` is a Literal — FastAPI rejects unknown values at
        # request validation with 422 before the handler runs.
        response = client.get("/v1/explore", params={"mode": "bogus"})
        assert response.status_code == 422, response.text


class TestExploreTags:
    async def test_tags_aggregated_and_ordered(
        self,
        client: TestClient,
        test_session,
    ) -> None:
        await _seed(test_session)
        response = client.get("/v1/explore/tags")
        assert response.status_code == 200, response.text
        tags = response.json()["tags"]
        # "apatia" appears in both published books (count 2), "absurdo"
        # in one (count 1). The draft's tags are excluded. Order: count
        # DESC then name ASC.
        assert tags == [
            {"name": "apatia", "count": 2},
            {"name": "absurdo", "count": 1},
        ]
