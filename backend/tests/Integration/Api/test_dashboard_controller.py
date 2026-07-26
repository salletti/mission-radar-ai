"""Integration tests for /api/dashboard endpoints — fake use cases, no DB.

Auth is bypassed via a dependency override on get_current_user_profile_id
(same pattern as the other fake-use-case overrides below) — these tests are
about controller wiring, not token verification (covered separately by
Auth0TokenVerifierGateway's own unit tests).
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from main import app
from src.Application.DTO.activity_event import ActivityEvent, ActivityHistoryPage
from src.Application.DTO.dashboard_summary import DashboardKpis, DashboardSummary, PipelineHealth
from src.Application.DTO.explainability_report import ExplainabilityReport, ScoreBreakdown
from src.Application.DTO.get_activity_history_query import GetActivityHistoryQuery
from src.Application.DTO.get_mission_details_query import GetMissionDetailsQuery
from src.Application.DTO.get_mission_history_query import GetMissionHistoryQuery
from src.Application.DTO.get_today_missions_query import GetTodayMissionsQuery
from src.Application.DTO.mission_match_detail import MissionMatchDetail
from src.Application.DTO.today_mission import TodayMission
from src.Application.UseCase.get_activity_history import GetActivityHistory
from src.Application.UseCase.get_dashboard_summary import GetDashboardSummary
from src.Application.UseCase.get_mission_details import GetMissionDetails
from src.Application.UseCase.get_mission_history import GetMissionHistory
from src.Application.UseCase.get_today_missions import GetTodayMissions
from src.Domain.Exception.domain_exceptions import MissionMatchNotFoundError
from src.Infrastructure.Api.Dependency.dependencies import (
    get_activity_history_use_case,
    get_current_user_profile_id,
    get_dashboard_summary_use_case,
    get_mission_details_use_case,
    get_mission_history_use_case,
    get_today_missions_use_case,
)

_NOW = datetime(2026, 6, 27, 10, 0, 0, tzinfo=timezone.utc)
_USER_ID = uuid4()
_MATCH_ID = uuid4()
_ANALYZED_ID = uuid4()
_RAW_ID = uuid4()

_FAKE_ACTIVITY_PAGE = ActivityHistoryPage(
    items=[
        ActivityEvent(
            type="MISSION_MATCH",
            occurred_at=_NOW,
            title="Senior Python Engineer",
            description="Mission Python full remote 700€/j.",
            mission_match_id=_MATCH_ID,
            score=85,
        )
    ],
    total=1,
    limit=20,
    offset=0,
)

_FAKE_TODAY_MISSION = TodayMission(
    mission_match_id=_MATCH_ID,
    analyzed_post_id=_ANALYZED_ID,
    raw_post_id=_RAW_ID,
    author_name="Alice Recruiter",
    content_excerpt="Mission Python FastAPI full remote",
    post_url="https://linkedin.com/posts/1",
    detected_stack=("python", "fastapi"),
    detected_contract_type="freelance",
    detected_remote_mode="full_remote",
    global_score=0.85,
    score_details={"semantic": 0.9, "contract": 1.0, "tjm": 0.7, "remote": 1.0},
    detected_tjm=700.0,
    title="Senior Python Engineer",
    company="Acme Corp",
    location="Paris",
)

_FAKE_DETAIL = MissionMatchDetail(
    mission_match_id=_MATCH_ID,
    analyzed_post_id=_ANALYZED_ID,
    raw_post_id=_RAW_ID,
    author_name="Alice Recruiter",
    author_url="https://linkedin.com/in/alice",
    content="Mission Python FastAPI full remote 700€/j #freelance",
    post_url="https://linkedin.com/posts/1",
    published_at=_NOW,
    title="Senior Python Engineer",
    company="Acme Corp",
    location="Paris",
    summary="Mission Python full remote 700€/j.",
    seniority="senior",
    detected_stack=("python", "fastapi"),
    detected_contract_type="freelance",
    detected_remote_mode="full_remote",
    detected_tjm=700.0,
    global_score=0.85,
    score_details={"semantic": 0.9, "contract": 1.0, "tjm": 0.7, "remote": 1.0},
    matched_at=_NOW,
    matched_skills=("python", "fastapi"),
    missing_skills=("kubernetes",),
    explanation=ExplainabilityReport(
        score_breakdown=ScoreBreakdown(contract=1.0, daily_rate=0.7),
        matching_reasons=(
            "Votre expérience python correspond à la stack demandée.",
            "Votre préférence de contrat (freelance) correspond au type proposé.",
        ),
        warnings=(),
        strong_points=("python", "fastapi"),
        missing_skills=("kubernetes",),
        recommendations=(),
    ),
)

_FAKE_SUMMARY = DashboardSummary(
    kpis=DashboardKpis(
        total_missions=10,
        new_today=3,
        average_score=72,
        last_refresh=_NOW,
        pipeline_status="completed",
    ),
    health=PipelineHealth(
        status="OK",
        last_pipeline_duration_seconds=34.5,
    ),
)


# ---------------------------------------------------------------------------
# Fake use cases
# ---------------------------------------------------------------------------


class _FakeGetActivityHistory(GetActivityHistory):
    def __init__(self, result: ActivityHistoryPage) -> None:  # type: ignore[override]
        self._result = result

    async def execute(self, query: GetActivityHistoryQuery) -> ActivityHistoryPage:
        return self._result


class _FakeGetTodayMissions(GetTodayMissions):
    def __init__(self, result: list[TodayMission]) -> None:  # type: ignore[override]
        self._result = result

    async def execute(self, query: GetTodayMissionsQuery) -> list[TodayMission]:
        return self._result


class _FakeGetMissionHistory(GetMissionHistory):
    def __init__(self, result: list[TodayMission]) -> None:  # type: ignore[override]
        self._result = result

    async def execute(self, query: GetMissionHistoryQuery) -> list[TodayMission]:
        return self._result[query.offset : query.offset + query.limit]


class _FakeGetMissionDetails(GetMissionDetails):
    def __init__(self, result: MissionMatchDetail | None = None) -> None:  # type: ignore[override]
        self._result = result

    async def execute(self, query: GetMissionDetailsQuery) -> MissionMatchDetail:
        if self._result is None:
            raise MissionMatchNotFoundError("not found")
        return self._result


class _FakeGetDashboardSummary(GetDashboardSummary):
    def __init__(self, result: DashboardSummary) -> None:  # type: ignore[override]
        self._result = result

    async def execute(self, user_profile_id: UUID) -> DashboardSummary:
        return self._result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def api_client() -> AsyncClient:
    app.dependency_overrides[get_current_user_profile_id] = lambda: _USER_ID
    app.dependency_overrides[get_activity_history_use_case] = lambda: _FakeGetActivityHistory(_FAKE_ACTIVITY_PAGE)
    app.dependency_overrides[get_today_missions_use_case] = lambda: _FakeGetTodayMissions([_FAKE_TODAY_MISSION])
    app.dependency_overrides[get_mission_history_use_case] = lambda: _FakeGetMissionHistory([_FAKE_TODAY_MISSION] * 5)
    app.dependency_overrides[get_mission_details_use_case] = lambda: _FakeGetMissionDetails(_FAKE_DETAIL)
    app.dependency_overrides[get_dashboard_summary_use_case] = lambda: _FakeGetDashboardSummary(_FAKE_SUMMARY)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client_unauthenticated() -> AsyncClient:
    """No dependency overrides at all — exercises the real auth dependency chain."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def api_client_not_found() -> AsyncClient:
    _empty_page = ActivityHistoryPage(items=[], total=0, limit=20, offset=0)
    app.dependency_overrides[get_current_user_profile_id] = lambda: _USER_ID
    app.dependency_overrides[get_activity_history_use_case] = lambda: _FakeGetActivityHistory(_empty_page)
    app.dependency_overrides[get_today_missions_use_case] = lambda: _FakeGetTodayMissions([])
    app.dependency_overrides[get_mission_history_use_case] = lambda: _FakeGetMissionHistory([])
    app.dependency_overrides[get_mission_details_use_case] = lambda: _FakeGetMissionDetails(None)
    app.dependency_overrides[get_dashboard_summary_use_case] = lambda: _FakeGetDashboardSummary(
        DashboardSummary(
            kpis=DashboardKpis(total_missions=0, new_today=0, average_score=0, last_refresh=None, pipeline_status=None),
            health=PipelineHealth(status="UNKNOWN", last_pipeline_duration_seconds=None),
        )
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — GET /api/dashboard/missions/today
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_today_missions_returns_200(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/dashboard/missions/today")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_today_missions_response_is_list(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/dashboard/missions/today")
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1


@pytest.mark.asyncio
async def test_today_missions_response_structure(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/dashboard/missions/today")
    item = response.json()[0]
    assert item["mission_match_id"] == str(_MATCH_ID)
    assert item["global_score"] == 0.85
    assert item["detected_contract_type"] == "freelance"
    assert item["title"] == "Senior Python Engineer"
    assert item["company"] == "Acme Corp"
    assert item["location"] == "Paris"
    assert "semantic" in item["score_details"]
    assert "python" in item["detected_stack"]


@pytest.mark.asyncio
async def test_today_missions_without_auth_returns_401(api_client_unauthenticated: AsyncClient) -> None:
    response = await api_client_unauthenticated.get("/api/dashboard/missions/today")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_today_missions_empty_list(api_client_not_found: AsyncClient) -> None:
    response = await api_client_not_found.get("/api/dashboard/missions/today")
    assert response.status_code == 200
    assert response.json() == []


# ---------------------------------------------------------------------------
# Tests — GET /api/dashboard/missions/history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_history_returns_200(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/dashboard/missions/history")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_history_respects_limit_query_param(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/dashboard/missions/history?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


# ---------------------------------------------------------------------------
# Tests — GET /api/dashboard/missions/{mission_match_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mission_detail_returns_200(api_client: AsyncClient) -> None:
    response = await api_client.get(f"/api/dashboard/missions/{_MATCH_ID}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_mission_detail_response_structure(api_client: AsyncClient) -> None:
    response = await api_client.get(f"/api/dashboard/missions/{_MATCH_ID}")
    data = response.json()
    assert data["mission_match_id"] == str(_MATCH_ID)
    assert data["content"] == "Mission Python FastAPI full remote 700€/j #freelance"
    assert data["summary"] == "Mission Python full remote 700€/j."
    assert data["author_url"] == "https://linkedin.com/in/alice"
    assert data["seniority"] == "senior"
    assert "published_at" in data
    assert "matched_at" in data
    assert data["title"] == "Senior Python Engineer"


@pytest.mark.asyncio
async def test_mission_detail_explainability_fields_present(api_client: AsyncClient) -> None:
    response = await api_client.get(f"/api/dashboard/missions/{_MATCH_ID}")
    data = response.json()
    assert "matched_skills" in data
    assert "missing_skills" in data
    assert "explanation" in data
    assert isinstance(data["matched_skills"], list)
    assert isinstance(data["missing_skills"], list)
    assert isinstance(data["explanation"], dict)
    assert "python" in data["matched_skills"]
    assert "kubernetes" in data["missing_skills"]
    assert "score_breakdown" in data["explanation"]
    assert "matching_reasons" in data["explanation"]
    assert len(data["explanation"]["matching_reasons"]) > 0
    assert data["explanation"]["score_breakdown"]["contract"] == 1.0
    assert data["explanation"]["score_breakdown"]["daily_rate"] == 0.7
    assert data["explanation"]["score_breakdown"]["skills"] is None


@pytest.mark.asyncio
async def test_mission_detail_not_found_returns_404(api_client_not_found: AsyncClient) -> None:
    response = await api_client_not_found.get(f"/api/dashboard/missions/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Mission not found"


# ---------------------------------------------------------------------------
# Tests — GET /api/dashboard/summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_returns_200(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/dashboard/summary")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_summary_response_structure(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/dashboard/summary")
    data = response.json()
    assert "kpis" in data
    assert "health" in data
    assert data["kpis"]["total_missions"] == 10
    assert data["kpis"]["new_today"] == 3
    assert data["kpis"]["average_score"] == 72
    assert data["kpis"]["pipeline_status"] == "completed"
    assert data["kpis"]["last_refresh"] is not None
    assert data["health"]["status"] == "OK"
    assert data["health"]["last_pipeline_duration_seconds"] == 34.5


# ---------------------------------------------------------------------------
# Tests — GET /api/dashboard/history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_activity_history_returns_200(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/dashboard/history")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_activity_history_response_structure(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/dashboard/history")
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert data["total"] == 1
    assert data["limit"] == 20
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_activity_history_item_structure(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/dashboard/history")
    item = response.json()["items"][0]
    assert item["type"] == "MISSION_MATCH"
    assert item["title"] == "Senior Python Engineer"
    assert item["description"] == "Mission Python full remote 700€/j."
    assert item["score"] == 85
    assert item["mission_match_id"] == str(_MATCH_ID)
    assert "occurred_at" in item


@pytest.mark.asyncio
async def test_activity_history_empty_page(api_client_not_found: AsyncClient) -> None:
    response = await api_client_not_found.get("/api/dashboard/history")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
