"""Integration tests for _run_refresh() — real PostgreSQL, mocked external gateways."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


from src.Application.Exception.application_error import PipelineAlreadyRunningError
from src.Application.UseCase.start_mission_refresh import StartMissionRefresh
from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.ValueObject.pipeline_enums import (
    PipelineStatus,
    PipelineStep,
    PipelineTrigger,
    StepOutcome,
)
from src.Infrastructure.Config.database import AsyncSessionLocal
from src.Infrastructure.Persistence.Repository.pipeline_run_repository import SqlAlchemyPipelineRunRepository
from src.Infrastructure.Persistence.Repository.user_profile_repository import SqlAlchemyUserProfileRepository
from src.Infrastructure.Worker.dispatchers.celery_pipeline_dispatcher import CeleryPipelineDispatcher
from src.Infrastructure.Worker.tasks.run_mission_refresh_task import _run_refresh

_MODULE = "src.Infrastructure.Worker.tasks.run_mission_refresh_task"


def _make_task() -> MagicMock:
    task = MagicMock()
    task.request.retries = 0
    return task


async def _fetch_run(run_id) -> PipelineRun:
    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyPipelineRunRepository(session)
        return await repo.get_by_id(run_id)


# ---------------------------------------------------------------------------
# Full pipeline happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_pipeline_completes(pending_pipeline_run: PipelineRun) -> None:
    """Pipeline complet collect → analyze → match → COMPLETED en base."""
    run = pending_pipeline_run

    with patch(f"{_MODULE}._collect_step", new=AsyncMock(return_value=[])), patch(
        f"{_MODULE}._analyze_step", new=AsyncMock()
    ), patch(f"{_MODULE}._match_step", new=AsyncMock()), patch(
        f"{_MODULE}._digest_step", new=AsyncMock()
    ):
        await _run_refresh(_make_task(), str(run.id), str(run.user_id))

    updated = await _fetch_run(run.id)
    assert updated.status == PipelineStatus.COMPLETED
    assert updated.current_step == PipelineStep.DONE
    assert updated.progress == 1.0
    assert updated.started_at is not None
    assert updated.finished_at is not None
    assert updated.error_message is None
    assert updated.step_outcomes.get(PipelineStep.DIGEST) == StepOutcome.SKIPPED


# ---------------------------------------------------------------------------
# Error during collect → FAILED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_error_marks_pipeline_failed(pending_pipeline_run: PipelineRun) -> None:
    """Erreur dans collect → status FAILED, error_message persisté en base."""
    run = pending_pipeline_run

    with patch(f"{_MODULE}._collect_step", new=AsyncMock(side_effect=RuntimeError("apify timeout"))):
        with pytest.raises(RuntimeError, match="apify timeout"):
            await _run_refresh(_make_task(), str(run.id), str(run.user_id))

    updated = await _fetch_run(run.id)
    assert updated.status == PipelineStatus.FAILED
    assert "apify timeout" in updated.error_message
    assert updated.finished_at is not None


# ---------------------------------------------------------------------------
# Error during analyze → FAILED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_error_marks_pipeline_failed(pending_pipeline_run: PipelineRun) -> None:
    """Erreur dans analyze → status FAILED persisté en base."""
    run = pending_pipeline_run

    with patch(f"{_MODULE}._collect_step", new=AsyncMock(return_value=[])), patch(
        f"{_MODULE}._analyze_step", new=AsyncMock(side_effect=RuntimeError("llm error"))
    ):
        with pytest.raises(RuntimeError, match="llm error"):
            await _run_refresh(_make_task(), str(run.id), str(run.user_id))

    updated = await _fetch_run(run.id)
    assert updated.status == PipelineStatus.FAILED
    assert "llm error" in updated.error_message


# ---------------------------------------------------------------------------
# Error during match → FAILED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_match_error_marks_pipeline_failed(pending_pipeline_run: PipelineRun) -> None:
    """Erreur dans match → status FAILED persisté en base."""
    run = pending_pipeline_run

    with patch(f"{_MODULE}._collect_step", new=AsyncMock(return_value=[])), patch(
        f"{_MODULE}._analyze_step", new=AsyncMock()
    ), patch(f"{_MODULE}._match_step", new=AsyncMock(side_effect=ValueError("profile missing"))):
        with pytest.raises(ValueError, match="profile missing"):
            await _run_refresh(_make_task(), str(run.id), str(run.user_id))

    updated = await _fetch_run(run.id)
    assert updated.status == PipelineStatus.FAILED
    assert "profile missing" in updated.error_message


# ---------------------------------------------------------------------------
# Double-launch prevention
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_second_launch_raises_pipeline_already_running(
    pending_pipeline_run: PipelineRun,
) -> None:
    """Un pipeline RUNNING bloque un deuxième StartMissionRefresh pour le même user."""
    run = pending_pipeline_run

    # Transition to RUNNING manually in DB
    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyPipelineRunRepository(session)
        run_entity = await repo.get_by_id(run.id)
        run_entity.start()
        await repo.update(run_entity)
        await session.commit()

    async with AsyncSessionLocal() as session:
        use_case = StartMissionRefresh(
            pipeline_run_repo=SqlAlchemyPipelineRunRepository(session),
            user_profile_repo=SqlAlchemyUserProfileRepository(session),
            dispatcher=MagicMock(spec=CeleryPipelineDispatcher),
        )
        with pytest.raises(PipelineAlreadyRunningError):
            await use_case.execute(run.user_id, PipelineTrigger.USER)
