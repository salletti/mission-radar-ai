"""Unit tests for PipelineResource — no I/O, no DB, no real MCP server. Fakes only."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.UseCase.get_pipeline_status import GetPipelineStatus
from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.Repository.pipeline_run_repository import PipelineRunRepository
from src.Domain.ValueObject.pipeline_enums import PipelineStatus, PipelineStep, PipelineTrigger, PipelineType
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver
from src.Infrastructure.Mcp.Resource.pipeline_resource import PipelineResource

_NOW = datetime.now(timezone.utc)


class FakePipelineRunRepository(PipelineRunRepository):
    def __init__(self, latest: Optional[PipelineRun] = None) -> None:
        self._latest = latest

    async def find_latest_for_user(self, user_id: UUID) -> Optional[PipelineRun]:
        return self._latest

    async def save(self, run: PipelineRun) -> None: ...
    async def get_by_id(self, run_id: UUID) -> Optional[PipelineRun]: return None
    async def find_running_for_user(self, user_id: UUID) -> Optional[PipelineRun]: return None
    async def update(self, run: PipelineRun) -> None: ...


class FakeIdentityResolver(IdentityResolver):
    def __init__(self, user_profile_id: UUID) -> None:
        self._user_profile_id = user_profile_id

    async def resolve(self) -> UUID:
        return self._user_profile_id


@pytest.mark.asyncio
async def test_pipeline_resource_returns_last_run_when_present() -> None:
    user_id = uuid4()
    run = PipelineRun(
        user_id=user_id,
        pipeline_type=PipelineType.MISSION_REFRESH,
        trigger_type=PipelineTrigger.USER,
        status=PipelineStatus.COMPLETED,
        current_step=PipelineStep.DONE,
        progress=1.0,
        started_at=_NOW - timedelta(seconds=40),
        finished_at=_NOW,
    )
    get_pipeline_status = GetPipelineStatus(pipeline_run_repository=FakePipelineRunRepository(latest=run))
    resource = PipelineResource(
        identity_resolver=FakeIdentityResolver(user_id), get_pipeline_status=get_pipeline_status
    )

    payload = await resource.execute()

    assert payload["last_run"]["id"] == str(run.id)
    assert payload["last_run"]["status"] == "completed"
    assert payload["last_run"]["current_step"] == "done"
    assert payload["last_run"]["progress"] == 1.0
    assert payload["last_run"]["started_at"] == run.started_at.isoformat()
    assert payload["last_run"]["finished_at"] == run.finished_at.isoformat()
    assert payload["last_run"]["error_message"] is None
    assert payload["last_run"]["step_outcomes"] == {}


@pytest.mark.asyncio
async def test_pipeline_resource_returns_null_last_run_when_never_run() -> None:
    user_id = uuid4()
    get_pipeline_status = GetPipelineStatus(pipeline_run_repository=FakePipelineRunRepository(latest=None))
    resource = PipelineResource(
        identity_resolver=FakeIdentityResolver(user_id), get_pipeline_status=get_pipeline_status
    )

    payload = await resource.execute()

    assert payload == {"last_run": None}
