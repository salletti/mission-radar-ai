"""Unit tests for StartMissionRefresh use case — no I/O, no DB."""
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
from src.Domain.ValueObject.pipeline_enums import (
    PipelineStatus,
    PipelineStep,
    PipelineTrigger,
    PipelineType,
)
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack

from datetime import datetime, timezone

_NOW = datetime(2026, 6, 27, tzinfo=timezone.utc)
_AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fake implementations
# ---------------------------------------------------------------------------


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

    async def update(self, run: PipelineRun) -> None:
        pass


class FakeUserProfileRepository(UserProfileRepository):
    def __init__(self, profile: Optional[UserProfile] = None) -> None:
        self._profile = profile

    async def save(self, profile: UserProfile) -> None:
        pass

    async def get_by_id(self, profile_id: UUID) -> Optional[UserProfile]:
        if self._profile and self._profile.id == profile_id:
            return self._profile
        return None

    async def get_by_email(self, email: str) -> Optional[UserProfile]:
        return None

    async def get_active_profile(self) -> Optional[UserProfile]:
        return self._profile

    async def delete(self, profile_id: UUID) -> None:
        pass


class FakePipelineDispatcher(PipelineDispatcherGateway):
    def __init__(self) -> None:
        self.dispatched: list[tuple[UUID, UUID]] = []

    def run_mission_refresh(self, pipeline_run_id: UUID, user_id: UUID) -> None:
        self.dispatched.append((pipeline_run_id, user_id))


def _make_profile(user_id: UUID | None = None) -> UserProfile:
    uid = user_id or uuid4()
    return UserProfile(
        id=uid,
        email=f"{uid}@test.com",
        full_name="Test User",
        title="Senior Python Engineer",
        years_experience=10,
        preferred_contract_type=ContractType.FREELANCE,
        target_tjm=700.0,
        preferred_remote_mode=RemoteMode.FULL_REMOTE,
        location="Paris",
        availability=_AVAILABILITY,
        skills=Stack.from_list(["Python", "FastAPI"]),
    )


def _make_pending_run(user_id: UUID | None = None) -> PipelineRun:
    return PipelineRun(
        user_id=user_id or uuid4(),
        pipeline_type=PipelineType.MISSION_REFRESH,
        trigger_type=PipelineTrigger.USER,
        status=PipelineStatus.RUNNING,
        current_step=PipelineStep.COLLECT,
        progress=0.0,
    )


def _make_use_case(
    profile: Optional[UserProfile] = None,
    running_run: Optional[PipelineRun] = None,
) -> tuple[StartMissionRefresh, FakePipelineRunRepository, FakePipelineDispatcher]:
    pipeline_repo = FakePipelineRunRepository(running_run=running_run)
    user_repo = FakeUserProfileRepository(profile=profile)
    dispatcher = FakePipelineDispatcher()
    use_case = StartMissionRefresh(
        pipeline_run_repo=pipeline_repo,
        user_profile_repo=user_repo,
        dispatcher=dispatcher,
    )
    return use_case, pipeline_repo, dispatcher


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_user_trigger_saves_pending_run() -> None:
    profile = _make_profile()
    use_case, repo, dispatcher = _make_use_case(profile=profile)

    run = await use_case.execute(profile.id, PipelineTrigger.USER)

    assert len(repo.saved) == 1
    assert repo.saved[0].status == PipelineStatus.PENDING
    assert run.status == PipelineStatus.PENDING


@pytest.mark.asyncio
async def test_happy_path_scheduler_trigger_sets_trigger_type() -> None:
    profile = _make_profile()
    use_case, repo, _ = _make_use_case(profile=profile)

    run = await use_case.execute(profile.id, PipelineTrigger.SCHEDULER)

    assert run.trigger_type == PipelineTrigger.SCHEDULER


@pytest.mark.asyncio
async def test_happy_path_pipeline_type_is_mission_refresh() -> None:
    profile = _make_profile()
    use_case, _, _ = _make_use_case(profile=profile)

    run = await use_case.execute(profile.id, PipelineTrigger.USER)

    assert run.pipeline_type == PipelineType.MISSION_REFRESH


@pytest.mark.asyncio
async def test_happy_path_initial_step_is_collect() -> None:
    profile = _make_profile()
    use_case, _, _ = _make_use_case(profile=profile)

    run = await use_case.execute(profile.id, PipelineTrigger.USER)

    assert run.current_step == PipelineStep.COLLECT


@pytest.mark.asyncio
async def test_happy_path_initial_progress_is_zero() -> None:
    profile = _make_profile()
    use_case, _, _ = _make_use_case(profile=profile)

    run = await use_case.execute(profile.id, PipelineTrigger.USER)

    assert run.progress == 0.0


@pytest.mark.asyncio
async def test_happy_path_dispatcher_called_once() -> None:
    profile = _make_profile()
    use_case, _, dispatcher = _make_use_case(profile=profile)

    run = await use_case.execute(profile.id, PipelineTrigger.USER)

    assert len(dispatcher.dispatched) == 1
    assert dispatcher.dispatched[0] == (run.id, profile.id)


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_not_found_raises_user_profile_not_found_error() -> None:
    use_case, repo, dispatcher = _make_use_case(profile=None)

    with pytest.raises(UserProfileNotFoundError):
        await use_case.execute(uuid4(), PipelineTrigger.USER)


@pytest.mark.asyncio
async def test_user_not_found_does_not_save_run() -> None:
    use_case, repo, _ = _make_use_case(profile=None)

    with pytest.raises(UserProfileNotFoundError):
        await use_case.execute(uuid4(), PipelineTrigger.USER)

    assert len(repo.saved) == 0


@pytest.mark.asyncio
async def test_user_not_found_does_not_dispatch() -> None:
    use_case, _, dispatcher = _make_use_case(profile=None)

    with pytest.raises(UserProfileNotFoundError):
        await use_case.execute(uuid4(), PipelineTrigger.USER)

    assert len(dispatcher.dispatched) == 0


@pytest.mark.asyncio
async def test_pipeline_already_running_raises() -> None:
    profile = _make_profile()
    existing_run = _make_pending_run(user_id=profile.id)
    use_case, _, _ = _make_use_case(profile=profile, running_run=existing_run)

    with pytest.raises(PipelineAlreadyRunningError):
        await use_case.execute(profile.id, PipelineTrigger.USER)


@pytest.mark.asyncio
async def test_pipeline_already_running_does_not_save_new_run() -> None:
    profile = _make_profile()
    existing_run = _make_pending_run(user_id=profile.id)
    use_case, repo, _ = _make_use_case(profile=profile, running_run=existing_run)

    with pytest.raises(PipelineAlreadyRunningError):
        await use_case.execute(profile.id, PipelineTrigger.USER)

    assert len(repo.saved) == 0


@pytest.mark.asyncio
async def test_pipeline_already_running_does_not_dispatch() -> None:
    profile = _make_profile()
    existing_run = _make_pending_run(user_id=profile.id)
    use_case, _, dispatcher = _make_use_case(profile=profile, running_run=existing_run)

    with pytest.raises(PipelineAlreadyRunningError):
        await use_case.execute(profile.id, PipelineTrigger.USER)

    assert len(dispatcher.dispatched) == 0
