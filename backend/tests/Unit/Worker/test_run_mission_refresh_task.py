"""Unit tests for _run_refresh() — no DB, no Celery broker, no external services."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.ValueObject.pipeline_enums import (
    PipelineStatus,
    PipelineStep,
    PipelineTrigger,
    PipelineType,
    StepOutcome,
)
from src.Infrastructure.Worker.tasks.run_mission_refresh_task import _run_refresh

_MODULE = "src.Infrastructure.Worker.tasks.run_mission_refresh_task"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run(
    status: PipelineStatus = PipelineStatus.PENDING,
    trigger_type: PipelineTrigger = PipelineTrigger.USER,
) -> PipelineRun:
    return PipelineRun(
        id=uuid4(),
        user_id=uuid4(),
        pipeline_type=PipelineType.MISSION_REFRESH,
        trigger_type=trigger_type,
        status=status,
        current_step=PipelineStep.COLLECT,
        progress=0.0,
    )


def _make_session_ctx() -> tuple[MagicMock, MagicMock]:
    """Returns (mock_AsyncSessionLocal, mock_session) for async with."""
    session = MagicMock()
    session.commit = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=ctx), session


def _make_task(retries: int = 0) -> MagicMock:
    task = MagicMock()
    task.request.retries = retries
    return task


# ---------------------------------------------------------------------------
# Happy path — USER trigger (digest SKIPPED)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_calls_start_and_no_fail() -> None:
    """Full happy path (USER trigger) — start() appelé, fail() jamais appelé, digest SKIPPED."""
    run = _make_run()
    mock_session_local, _ = _make_session_ctx()
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=run)
    mock_repo.update = AsyncMock()

    with (
        patch(f"{_MODULE}.AsyncSessionLocal", mock_session_local),
        patch(f"{_MODULE}.SqlAlchemyPipelineRunRepository", return_value=mock_repo),
        patch(f"{_MODULE}._collect_step", new=AsyncMock(return_value=[])),
        patch(f"{_MODULE}._analyze_step", new=AsyncMock()),
        patch(f"{_MODULE}._match_step", new=AsyncMock()),
        patch(f"{_MODULE}._digest_step", new=AsyncMock()) as mock_digest,
    ):
        await _run_refresh(_make_task(), str(run.id), str(run.user_id))

    # USER trigger → DigestPolicy returns False → _digest_step NOT called
    mock_digest.assert_not_awaited()
    assert run.status == PipelineStatus.COMPLETED


# ---------------------------------------------------------------------------
# PipelineRun not found
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pipeline_run_not_found_retries() -> None:
    """PipelineRun introuvable → task.retry() déclenché, aucune étape déclenchée."""
    mock_session_local, _ = _make_session_ctx()
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=None)

    mock_task = _make_task()
    mock_task.retry = MagicMock(side_effect=Exception("retry"))

    with (
        patch(f"{_MODULE}.AsyncSessionLocal", mock_session_local),
        patch(f"{_MODULE}.SqlAlchemyPipelineRunRepository", return_value=mock_repo),
        patch(f"{_MODULE}._collect_step", new=AsyncMock(return_value=[])) as mock_collect,
    ):
        with pytest.raises(Exception, match="retry"):
            await _run_refresh(mock_task, str(uuid4()), str(uuid4()))

    mock_collect.assert_not_awaited()


# ---------------------------------------------------------------------------
# Collect error → FAILED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_error_marks_failed_and_reraises() -> None:
    """Erreur dans _collect_step → run.fail() appelé, exception re-raised."""
    run_pending = _make_run(status=PipelineStatus.PENDING)
    mock_repo_start = MagicMock()
    mock_repo_start.get_by_id = AsyncMock(return_value=run_pending)
    mock_repo_start.update = AsyncMock()

    run_running = _make_run(status=PipelineStatus.RUNNING)
    mock_repo_fail = MagicMock()
    mock_repo_fail.get_by_id = AsyncMock(return_value=run_running)
    mock_repo_fail.update = AsyncMock()

    call_count = 0

    def repo_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_repo_start if call_count == 1 else mock_repo_fail

    mock_session_local, _ = _make_session_ctx()

    with (
        patch(f"{_MODULE}.AsyncSessionLocal", mock_session_local),
        patch(f"{_MODULE}.SqlAlchemyPipelineRunRepository", side_effect=repo_factory),
        patch(f"{_MODULE}._collect_step", new=AsyncMock(side_effect=RuntimeError("apify down"))),
    ):
        with pytest.raises(RuntimeError, match="apify down"):
            await _run_refresh(_make_task(), str(run_pending.id), str(run_pending.user_id))

    assert run_running.status == PipelineStatus.FAILED
    assert "apify down" in run_running.error_message
    mock_repo_fail.update.assert_awaited_once()


# ---------------------------------------------------------------------------
# Analyze error → FAILED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_error_marks_failed_and_reraises() -> None:
    """Erreur dans _analyze_step → run.fail() appelé, exception re-raised."""
    run_pending = _make_run(status=PipelineStatus.PENDING)
    mock_repo_start = MagicMock()
    mock_repo_start.get_by_id = AsyncMock(return_value=run_pending)
    mock_repo_start.update = AsyncMock()

    run_running = _make_run(status=PipelineStatus.RUNNING)
    mock_repo_fail = MagicMock()
    mock_repo_fail.get_by_id = AsyncMock(return_value=run_running)
    mock_repo_fail.update = AsyncMock()

    call_count = 0

    def repo_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_repo_start if call_count == 1 else mock_repo_fail

    mock_session_local, _ = _make_session_ctx()

    with (
        patch(f"{_MODULE}.AsyncSessionLocal", mock_session_local),
        patch(f"{_MODULE}.SqlAlchemyPipelineRunRepository", side_effect=repo_factory),
        patch(f"{_MODULE}._collect_step", new=AsyncMock(return_value=[])),
        patch(f"{_MODULE}._analyze_step", new=AsyncMock(side_effect=RuntimeError("llm error"))),
    ):
        with pytest.raises(RuntimeError, match="llm error"):
            await _run_refresh(_make_task(), str(run_pending.id), str(run_pending.user_id))

    assert run_running.status == PipelineStatus.FAILED
    assert "llm error" in run_running.error_message


# ---------------------------------------------------------------------------
# Match error → FAILED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_match_error_marks_failed_and_reraises() -> None:
    """Erreur dans _match_step → run.fail() appelé, exception re-raised."""
    run_pending = _make_run(status=PipelineStatus.PENDING)
    mock_repo_start = MagicMock()
    mock_repo_start.get_by_id = AsyncMock(return_value=run_pending)
    mock_repo_start.update = AsyncMock()

    run_running = _make_run(status=PipelineStatus.RUNNING)
    mock_repo_fail = MagicMock()
    mock_repo_fail.get_by_id = AsyncMock(return_value=run_running)
    mock_repo_fail.update = AsyncMock()

    call_count = 0

    def repo_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_repo_start if call_count == 1 else mock_repo_fail

    mock_session_local, _ = _make_session_ctx()

    with (
        patch(f"{_MODULE}.AsyncSessionLocal", mock_session_local),
        patch(f"{_MODULE}.SqlAlchemyPipelineRunRepository", side_effect=repo_factory),
        patch(f"{_MODULE}._collect_step", new=AsyncMock(return_value=[])),
        patch(f"{_MODULE}._analyze_step", new=AsyncMock()),
        patch(f"{_MODULE}._match_step", new=AsyncMock(side_effect=ValueError("no profile"))),
    ):
        with pytest.raises(ValueError, match="no profile"):
            await _run_refresh(_make_task(), str(run_pending.id), str(run_pending.user_id))

    assert run_running.status == PipelineStatus.FAILED
    assert "no profile" in run_running.error_message


# ---------------------------------------------------------------------------
# DigestPolicy — USER trigger → SKIPPED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_trigger_skips_digest() -> None:
    """USER trigger → DigestPolicy returns False → digest SKIPPED, pipeline COMPLETED."""
    run = _make_run(trigger_type=PipelineTrigger.USER)
    mock_session_local, _ = _make_session_ctx()
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=run)
    mock_repo.update = AsyncMock()

    with (
        patch(f"{_MODULE}.AsyncSessionLocal", mock_session_local),
        patch(f"{_MODULE}.SqlAlchemyPipelineRunRepository", return_value=mock_repo),
        patch(f"{_MODULE}._collect_step", new=AsyncMock(return_value=[])),
        patch(f"{_MODULE}._analyze_step", new=AsyncMock()),
        patch(f"{_MODULE}._match_step", new=AsyncMock()),
        patch(f"{_MODULE}._digest_step", new=AsyncMock()) as mock_digest,
    ):
        await _run_refresh(_make_task(), str(run.id), str(run.user_id))

    mock_digest.assert_not_awaited()
    assert run.status == PipelineStatus.COMPLETED
    assert run.step_outcomes.get(PipelineStep.DIGEST) == StepOutcome.SKIPPED


# ---------------------------------------------------------------------------
# DigestPolicy — SCHEDULER trigger → EXECUTED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scheduler_trigger_executes_digest() -> None:
    """SCHEDULER trigger → DigestPolicy returns True → _digest_step called, digest EXECUTED."""
    run = _make_run(trigger_type=PipelineTrigger.SCHEDULER)
    mock_session_local, _ = _make_session_ctx()
    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value=run)
    mock_repo.update = AsyncMock()

    with (
        patch(f"{_MODULE}.AsyncSessionLocal", mock_session_local),
        patch(f"{_MODULE}.SqlAlchemyPipelineRunRepository", return_value=mock_repo),
        patch(f"{_MODULE}.settings.DIGEST_ENABLED", True),
        patch(f"{_MODULE}._collect_step", new=AsyncMock(return_value=[])),
        patch(f"{_MODULE}._analyze_step", new=AsyncMock()),
        patch(f"{_MODULE}._match_step", new=AsyncMock()),
        patch(f"{_MODULE}._digest_step", new=AsyncMock()) as mock_digest,
    ):
        await _run_refresh(_make_task(), str(run.id), str(run.user_id))

    mock_digest.assert_awaited_once()
    assert run.status == PipelineStatus.COMPLETED
    assert run.step_outcomes.get(PipelineStep.DIGEST) == StepOutcome.EXECUTED


# ---------------------------------------------------------------------------
# Digest error → FAILED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_digest_error_marks_pipeline_failed() -> None:
    """Erreur dans _digest_step → run.fail() appelé, pipeline FAILED."""
    run_pending = _make_run(status=PipelineStatus.PENDING, trigger_type=PipelineTrigger.SCHEDULER)
    mock_repo_start = MagicMock()
    mock_repo_start.get_by_id = AsyncMock(return_value=run_pending)
    mock_repo_start.update = AsyncMock()

    run_running = _make_run(status=PipelineStatus.RUNNING, trigger_type=PipelineTrigger.SCHEDULER)
    mock_repo_fail = MagicMock()
    mock_repo_fail.get_by_id = AsyncMock(return_value=run_running)
    mock_repo_fail.update = AsyncMock()

    call_count = 0

    def repo_factory(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return mock_repo_start if call_count == 1 else mock_repo_fail

    mock_session_local, _ = _make_session_ctx()

    with (
        patch(f"{_MODULE}.AsyncSessionLocal", mock_session_local),
        patch(f"{_MODULE}.SqlAlchemyPipelineRunRepository", side_effect=repo_factory),
        patch(f"{_MODULE}.settings.DIGEST_ENABLED", True),
        patch(f"{_MODULE}._collect_step", new=AsyncMock(return_value=[])),
        patch(f"{_MODULE}._analyze_step", new=AsyncMock()),
        patch(f"{_MODULE}._match_step", new=AsyncMock()),
        patch(f"{_MODULE}._digest_step", new=AsyncMock(side_effect=RuntimeError("resend down"))),
    ):
        with pytest.raises(RuntimeError, match="resend down"):
            await _run_refresh(_make_task(), str(run_pending.id), str(run_pending.user_id))

    assert run_running.status == PipelineStatus.FAILED
    assert "resend down" in run_running.error_message
