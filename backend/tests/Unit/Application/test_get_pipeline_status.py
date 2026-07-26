"""Unit tests for GetPipelineStatus use case — no I/O, no DB."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.UseCase.get_pipeline_status import GetPipelineStatus
from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.Repository.pipeline_run_repository import PipelineRunRepository
from src.Domain.ValueObject.pipeline_enums import (
    PipelineStatus,
    PipelineStep,
    PipelineTrigger,
    PipelineType,
    StepOutcome,
)

_NOW = datetime.now(timezone.utc)
_USER_ID = uuid4()


class FakePipelineRunRepository(PipelineRunRepository):
    def __init__(self, latest: Optional[PipelineRun] = None) -> None:
        self._latest = latest

    async def find_latest_for_user(self, user_id: UUID) -> Optional[PipelineRun]:
        return self._latest

    async def save(self, run: PipelineRun) -> None: ...
    async def get_by_id(self, run_id: UUID) -> Optional[PipelineRun]: return None
    async def find_running_for_user(self, user_id: UUID) -> Optional[PipelineRun]: return None
    async def update(self, run: PipelineRun) -> None: ...


def _make_run() -> PipelineRun:
    run = PipelineRun(
        user_id=_USER_ID,
        pipeline_type=PipelineType.MISSION_REFRESH,
        trigger_type=PipelineTrigger.USER,
        status=PipelineStatus.COMPLETED,
        current_step=PipelineStep.DONE,
        progress=1.0,
        started_at=_NOW - timedelta(seconds=40),
        finished_at=_NOW,
    )
    run.record_step_outcome(PipelineStep.COLLECT, StepOutcome.EXECUTED)
    return run


@pytest.mark.asyncio
async def test_returns_flattened_dto_for_latest_run() -> None:
    run = _make_run()
    use_case = GetPipelineStatus(pipeline_run_repository=FakePipelineRunRepository(latest=run))

    result = await use_case.execute(_USER_ID)

    assert result.id == run.id
    assert result.status == "completed"
    assert result.current_step == "done"
    assert result.progress == 1.0
    assert result.started_at == run.started_at
    assert result.finished_at == run.finished_at
    assert result.error_message is None
    assert result.step_outcomes == {"collect": "executed"}


@pytest.mark.asyncio
async def test_returns_none_when_no_run_yet() -> None:
    use_case = GetPipelineStatus(pipeline_run_repository=FakePipelineRunRepository(latest=None))

    result = await use_case.execute(_USER_ID)

    assert result is None
