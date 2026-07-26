"""Integration tests for pipeline API endpoints — fake use case, no DB.

Auth is bypassed via a dependency override on get_current_user_profile_id —
these tests are about controller wiring, not token verification (covered
separately by Auth0TokenVerifierGateway's own unit tests).
"""
from typing import Optional
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from main import app
from src.Application.Exception.application_error import PipelineAlreadyRunningError, UserProfileNotFoundError
from src.Application.UseCase.start_mission_refresh import StartMissionRefresh
from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.ValueObject.pipeline_enums import (
    PipelineStatus,
    PipelineStep,
    PipelineTrigger,
    PipelineType,
)
from src.Infrastructure.Api.Dependency.dependencies import get_current_user_profile_id
from src.Infrastructure.Api.Dependency.pipeline_dependencies import (
    get_pipeline_run_repository,
    get_start_mission_refresh,
)
from src.Infrastructure.Persistence.Repository.pipeline_run_repository import SqlAlchemyPipelineRunRepository

_KNOWN_USER_ID = uuid4()
_KNOWN_RUN_ID = uuid4()


def _make_pending_run(user_id: UUID | None = None, run_id: UUID | None = None) -> PipelineRun:
    return PipelineRun(
        id=run_id or _KNOWN_RUN_ID,
        user_id=user_id or _KNOWN_USER_ID,
        pipeline_type=PipelineType.MISSION_REFRESH,
        trigger_type=PipelineTrigger.USER,
        status=PipelineStatus.PENDING,
        current_step=PipelineStep.COLLECT,
        progress=0.0,
    )


# ---------------------------------------------------------------------------
# Fake StartMissionRefresh implementations
# ---------------------------------------------------------------------------


class _FakeStartMissionRefreshOk(StartMissionRefresh):
    def __init__(self) -> None:  # type: ignore[override]
        pass

    async def execute(self, user_id: UUID, trigger: PipelineTrigger) -> PipelineRun:
        return _make_pending_run(user_id=user_id)


class _FakeStartMissionRefreshUserNotFound(StartMissionRefresh):
    def __init__(self) -> None:  # type: ignore[override]
        pass

    async def execute(self, user_id: UUID, trigger: PipelineTrigger) -> PipelineRun:
        raise UserProfileNotFoundError(f"User {user_id} not found")


class _FakeStartMissionRefreshAlreadyRunning(StartMissionRefresh):
    def __init__(self) -> None:  # type: ignore[override]
        pass

    async def execute(self, user_id: UUID, trigger: PipelineTrigger) -> PipelineRun:
        raise PipelineAlreadyRunningError("Pipeline already running")


# ---------------------------------------------------------------------------
# Fake SqlAlchemyPipelineRunRepository for GET endpoint
# ---------------------------------------------------------------------------


class _FakePipelineRunRepositoryFound(SqlAlchemyPipelineRunRepository):
    def __init__(self) -> None:  # type: ignore[override]
        pass

    async def get_by_id(self, run_id: UUID) -> Optional[PipelineRun]:
        if run_id == _KNOWN_RUN_ID:
            return _make_pending_run()
        return None

    async def save(self, run: PipelineRun) -> None:
        pass

    async def find_latest_for_user(self, user_id: UUID) -> Optional[PipelineRun]:
        return None

    async def find_running_for_user(self, user_id: UUID) -> Optional[PipelineRun]:
        return None

    async def update(self, run: PipelineRun) -> None:
        pass


class _FakePipelineRunRepositoryNotFound(SqlAlchemyPipelineRunRepository):
    def __init__(self) -> None:  # type: ignore[override]
        pass

    async def get_by_id(self, run_id: UUID) -> Optional[PipelineRun]:
        return None

    async def save(self, run: PipelineRun) -> None:
        pass

    async def find_latest_for_user(self, user_id: UUID) -> Optional[PipelineRun]:
        return None

    async def find_running_for_user(self, user_id: UUID) -> Optional[PipelineRun]:
        return None

    async def update(self, run: PipelineRun) -> None:
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def api_client_ok() -> AsyncClient:
    app.dependency_overrides[get_current_user_profile_id] = lambda: _KNOWN_USER_ID
    app.dependency_overrides[get_start_mission_refresh] = lambda: _FakeStartMissionRefreshOk()
    app.dependency_overrides[get_pipeline_run_repository] = lambda: _FakePipelineRunRepositoryFound()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client_user_not_found() -> AsyncClient:
    app.dependency_overrides[get_current_user_profile_id] = lambda: _KNOWN_USER_ID
    app.dependency_overrides[get_start_mission_refresh] = lambda: _FakeStartMissionRefreshUserNotFound()
    app.dependency_overrides[get_pipeline_run_repository] = lambda: _FakePipelineRunRepositoryNotFound()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client_already_running() -> AsyncClient:
    app.dependency_overrides[get_current_user_profile_id] = lambda: _KNOWN_USER_ID
    app.dependency_overrides[get_start_mission_refresh] = lambda: _FakeStartMissionRefreshAlreadyRunning()
    app.dependency_overrides[get_pipeline_run_repository] = lambda: _FakePipelineRunRepositoryFound()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client_unauthenticated() -> AsyncClient:
    """No dependency overrides at all — exercises the real auth dependency chain."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


# ---------------------------------------------------------------------------
# POST /api/pipelines/mission-refresh
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_mission_refresh_returns_200(api_client_ok: AsyncClient) -> None:
    response = await api_client_ok.post("/api/pipelines/mission-refresh")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_start_mission_refresh_returns_pending_status(api_client_ok: AsyncClient) -> None:
    response = await api_client_ok.post("/api/pipelines/mission-refresh")
    data = response.json()
    assert data["status"] == "pending"
    assert data["current_step"] == "collect"
    assert data["progress"] == 0.0
    assert data["pipeline_type"] == "mission_refresh"
    assert data["trigger_type"] == "user"


@pytest.mark.asyncio
async def test_start_mission_refresh_user_not_found_returns_404(
    api_client_user_not_found: AsyncClient,
) -> None:
    response = await api_client_user_not_found.post("/api/pipelines/mission-refresh")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_start_mission_refresh_already_running_returns_409(
    api_client_already_running: AsyncClient,
) -> None:
    response = await api_client_already_running.post("/api/pipelines/mission-refresh")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_start_mission_refresh_without_auth_returns_401(
    api_client_unauthenticated: AsyncClient,
) -> None:
    response = await api_client_unauthenticated.post("/api/pipelines/mission-refresh")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/pipelines/{pipeline_run_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_pipeline_run_returns_200(api_client_ok: AsyncClient) -> None:
    response = await api_client_ok.get(f"/api/pipelines/{_KNOWN_RUN_ID}")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_pipeline_run_returns_all_fields(api_client_ok: AsyncClient) -> None:
    response = await api_client_ok.get(f"/api/pipelines/{_KNOWN_RUN_ID}")
    data = response.json()
    assert "id" in data
    assert "user_id" in data
    assert "pipeline_type" in data
    assert "trigger_type" in data
    assert "status" in data
    assert "current_step" in data
    assert "progress" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_pipeline_run_not_found_returns_404(
    api_client_user_not_found: AsyncClient,
) -> None:
    response = await api_client_user_not_found.get(f"/api/pipelines/{uuid4()}")
    assert response.status_code == 404
