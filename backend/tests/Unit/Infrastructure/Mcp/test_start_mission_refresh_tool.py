"""Unit tests for StartMissionRefreshTool — no I/O, no DB, no real MCP server. Fakes only."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.Exception.application_error import PipelineAlreadyRunningError, UserProfileNotFoundError
from src.Application.Gateway.pipeline_dispatcher_gateway import PipelineDispatcherGateway
from src.Application.UseCase.start_mission_refresh import StartMissionRefresh
from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Repository.pipeline_run_repository import PipelineRunRepository
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.pipeline_enums import PipelineStatus, PipelineStep, PipelineTrigger, PipelineType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver
from src.Infrastructure.Mcp.Tool.start_mission_refresh_tool import StartMissionRefreshTool


class FakePipelineRunRepository(PipelineRunRepository):
    def __init__(self, running_run: Optional[PipelineRun] = None) -> None:
        self.saved: list[PipelineRun] = []
        self._running = running_run

    async def save(self, run: PipelineRun) -> None:
        self.saved.append(run)

    async def get_by_id(self, run_id: UUID) -> Optional[PipelineRun]:
        return next((r for r in self.saved if r.id == run_id), None)

    async def find_latest_for_user(self, user_id: UUID) -> Optional[PipelineRun]:
        return None

    async def find_running_for_user(self, user_id: UUID) -> Optional[PipelineRun]:
        return self._running

    async def update(self, run: PipelineRun) -> None: ...


class FakeUserProfileRepository(UserProfileRepository):
    def __init__(self, profile: Optional[UserProfile] = None) -> None:
        self._profile = profile

    async def save(self, profile: UserProfile) -> None: ...
    async def get_by_email(self, email: str) -> Optional[UserProfile]: return None
    async def get_active_profile(self) -> Optional[UserProfile]: return self._profile
    async def delete(self, profile_id: UUID) -> None: ...

    async def get_by_id(self, profile_id: UUID) -> Optional[UserProfile]:
        if self._profile and self._profile.id == profile_id:
            return self._profile
        return None


class FakePipelineDispatcher(PipelineDispatcherGateway):
    def __init__(self) -> None:
        self.dispatched: list[tuple[UUID, UUID]] = []

    def run_mission_refresh(self, pipeline_run_id: UUID, user_id: UUID) -> None:
        self.dispatched.append((pipeline_run_id, user_id))


class FakeIdentityResolver(IdentityResolver):
    def __init__(self, user_profile_id: UUID) -> None:
        self._user_profile_id = user_profile_id

    async def resolve(self) -> UUID:
        return self._user_profile_id


def _make_profile(user_id: UUID) -> UserProfile:
    return UserProfile(
        id=user_id,
        email="freelancer@example.com",
        full_name="Jean Dupont",
        title="Senior Python Engineer",
        years_experience=10,
        preferred_contract_type=ContractType.FREELANCE,
        target_tjm=700.0,
        preferred_remote_mode=RemoteMode.FULL_REMOTE,
        skills=Stack.from_list(["python", "fastapi"]),
        location="Paris",
        availability=datetime(2026, 9, 1, tzinfo=timezone.utc),
    )


def _make_running_run(user_id: UUID) -> PipelineRun:
    return PipelineRun(
        user_id=user_id,
        pipeline_type=PipelineType.MISSION_REFRESH,
        trigger_type=PipelineTrigger.USER,
        status=PipelineStatus.RUNNING,
        current_step=PipelineStep.COLLECT,
        progress=0.0,
    )


def _make_tool(
    identity_resolver: FakeIdentityResolver,
    profile: Optional[UserProfile] = None,
    running_run: Optional[PipelineRun] = None,
) -> tuple[StartMissionRefreshTool, FakePipelineRunRepository, FakePipelineDispatcher]:
    pipeline_repo = FakePipelineRunRepository(running_run=running_run)
    user_repo = FakeUserProfileRepository(profile=profile)
    dispatcher = FakePipelineDispatcher()
    start_mission_refresh = StartMissionRefresh(
        pipeline_run_repo=pipeline_repo, user_profile_repo=user_repo, dispatcher=dispatcher
    )
    tool = StartMissionRefreshTool(identity_resolver=identity_resolver, start_mission_refresh=start_mission_refresh)
    return tool, pipeline_repo, dispatcher


@pytest.mark.asyncio
async def test_start_mission_refresh_returns_pending_run_payload() -> None:
    user_id = uuid4()
    tool, repo, dispatcher = _make_tool(FakeIdentityResolver(user_id), profile=_make_profile(user_id))

    payload = await tool.execute()

    assert payload["user_id"] == str(user_id)
    assert payload["pipeline_type"] == "mission_refresh"
    assert payload["trigger_type"] == "user"
    assert payload["status"] == "pending"
    assert payload["current_step"] == "collect"
    assert payload["progress"] == 0.0
    assert payload["started_at"] is None
    assert payload["finished_at"] is None
    assert payload["error_message"] is None
    assert payload["step_outcomes"] == {}
    assert len(repo.saved) == 1
    assert len(dispatcher.dispatched) == 1


@pytest.mark.asyncio
async def test_start_mission_refresh_raises_when_pipeline_already_running() -> None:
    user_id = uuid4()
    tool, repo, dispatcher = _make_tool(
        FakeIdentityResolver(user_id), profile=_make_profile(user_id), running_run=_make_running_run(user_id)
    )

    with pytest.raises(PipelineAlreadyRunningError):
        await tool.execute()

    assert len(repo.saved) == 0
    assert len(dispatcher.dispatched) == 0


@pytest.mark.asyncio
async def test_start_mission_refresh_raises_when_user_not_found() -> None:
    tool, repo, dispatcher = _make_tool(FakeIdentityResolver(uuid4()), profile=None)

    with pytest.raises(UserProfileNotFoundError):
        await tool.execute()

    assert len(repo.saved) == 0
    assert len(dispatcher.dispatched) == 0
