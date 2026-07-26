"""Unit tests for PipelineRun state machine — no I/O."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.Exception.domain_exceptions import InvalidPipelineTransitionError
from src.Domain.ValueObject.pipeline_enums import (
    PipelineStatus,
    PipelineStep,
    PipelineTrigger,
    PipelineType,
    StepOutcome,
)


def _make_run(**kwargs) -> PipelineRun:
    defaults = dict(
        user_id=uuid4(),
        pipeline_type=PipelineType.MISSION_REFRESH,
        trigger_type=PipelineTrigger.USER,
        status=PipelineStatus.PENDING,
        current_step=PipelineStep.COLLECT,
        progress=0.0,
    )
    return PipelineRun(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Creation defaults
# ---------------------------------------------------------------------------


def test_creation_defaults() -> None:
    run = _make_run()
    assert run.status == PipelineStatus.PENDING
    assert run.current_step == PipelineStep.COLLECT
    assert run.progress == 0.0
    assert run.started_at is None
    assert run.finished_at is None
    assert run.error_message is None
    assert run.pipeline_type == PipelineType.MISSION_REFRESH


def test_created_at_is_set_automatically() -> None:
    before = datetime.now(timezone.utc)
    run = _make_run()
    after = datetime.now(timezone.utc)
    assert run.created_at is not None
    assert before <= run.created_at <= after


# ---------------------------------------------------------------------------
# start()
# ---------------------------------------------------------------------------


def test_start_pending_transitions_to_running() -> None:
    run = _make_run(status=PipelineStatus.PENDING)
    run.start()
    assert run.status == PipelineStatus.RUNNING


def test_start_sets_started_at() -> None:
    before = datetime.now(timezone.utc)
    run = _make_run(status=PipelineStatus.PENDING)
    run.start()
    after = datetime.now(timezone.utc)
    assert run.started_at is not None
    assert before <= run.started_at <= after


def test_start_sets_progress_from_current_step() -> None:
    run = _make_run(status=PipelineStatus.PENDING, current_step=PipelineStep.COLLECT)
    run.start()
    assert run.progress == 0.25


def test_start_from_running_raises() -> None:
    run = _make_run(status=PipelineStatus.RUNNING)
    with pytest.raises(InvalidPipelineTransitionError):
        run.start()


def test_start_from_completed_raises() -> None:
    run = _make_run(status=PipelineStatus.COMPLETED)
    with pytest.raises(InvalidPipelineTransitionError):
        run.start()


def test_start_from_failed_raises() -> None:
    run = _make_run(status=PipelineStatus.FAILED)
    with pytest.raises(InvalidPipelineTransitionError):
        run.start()


# ---------------------------------------------------------------------------
# complete()
# ---------------------------------------------------------------------------


def test_complete_running_transitions_to_completed() -> None:
    run = _make_run(status=PipelineStatus.RUNNING)
    run.complete()
    assert run.status == PipelineStatus.COMPLETED


def test_complete_sets_finished_at() -> None:
    before = datetime.now(timezone.utc)
    run = _make_run(status=PipelineStatus.RUNNING)
    run.complete()
    after = datetime.now(timezone.utc)
    assert run.finished_at is not None
    assert before <= run.finished_at <= after


def test_complete_sets_progress_to_one() -> None:
    run = _make_run(status=PipelineStatus.RUNNING, progress=0.5)
    run.complete()
    assert run.progress == 1.0


def test_complete_from_pending_raises() -> None:
    run = _make_run(status=PipelineStatus.PENDING)
    with pytest.raises(InvalidPipelineTransitionError):
        run.complete()


def test_complete_from_failed_raises() -> None:
    run = _make_run(status=PipelineStatus.FAILED)
    with pytest.raises(InvalidPipelineTransitionError):
        run.complete()


# ---------------------------------------------------------------------------
# fail()
# ---------------------------------------------------------------------------


def test_fail_running_transitions_to_failed() -> None:
    run = _make_run(status=PipelineStatus.RUNNING)
    run.fail("timeout error")
    assert run.status == PipelineStatus.FAILED


def test_fail_sets_error_message() -> None:
    run = _make_run(status=PipelineStatus.RUNNING)
    run.fail("LLM call failed")
    assert run.error_message == "LLM call failed"


def test_fail_sets_finished_at() -> None:
    before = datetime.now(timezone.utc)
    run = _make_run(status=PipelineStatus.RUNNING)
    run.fail("error")
    after = datetime.now(timezone.utc)
    assert run.finished_at is not None
    assert before <= run.finished_at <= after


def test_fail_from_pending_raises() -> None:
    run = _make_run(status=PipelineStatus.PENDING)
    with pytest.raises(InvalidPipelineTransitionError):
        run.fail("error")


def test_fail_from_completed_raises() -> None:
    run = _make_run(status=PipelineStatus.COMPLETED)
    with pytest.raises(InvalidPipelineTransitionError):
        run.fail("error")


# ---------------------------------------------------------------------------
# cancel()
# ---------------------------------------------------------------------------


def test_cancel_running_transitions_to_cancelled() -> None:
    run = _make_run(status=PipelineStatus.RUNNING)
    run.cancel()
    assert run.status == PipelineStatus.CANCELLED


def test_cancel_sets_finished_at() -> None:
    before = datetime.now(timezone.utc)
    run = _make_run(status=PipelineStatus.RUNNING)
    run.cancel()
    after = datetime.now(timezone.utc)
    assert run.finished_at is not None
    assert before <= run.finished_at <= after


def test_cancel_from_pending_raises() -> None:
    run = _make_run(status=PipelineStatus.PENDING)
    with pytest.raises(InvalidPipelineTransitionError):
        run.cancel()


def test_cancel_from_completed_raises() -> None:
    run = _make_run(status=PipelineStatus.COMPLETED)
    with pytest.raises(InvalidPipelineTransitionError):
        run.cancel()


# ---------------------------------------------------------------------------
# advance_to_step()
# ---------------------------------------------------------------------------


def test_advance_collect_to_analyze() -> None:
    run = _make_run(current_step=PipelineStep.COLLECT)
    run.advance_to_step(PipelineStep.ANALYZE)
    assert run.current_step == PipelineStep.ANALYZE


def test_advance_analyze_to_match() -> None:
    run = _make_run(current_step=PipelineStep.ANALYZE)
    run.advance_to_step(PipelineStep.MATCH)
    assert run.current_step == PipelineStep.MATCH


def test_advance_match_to_digest() -> None:
    run = _make_run(current_step=PipelineStep.MATCH)
    run.advance_to_step(PipelineStep.DIGEST)
    assert run.current_step == PipelineStep.DIGEST


def test_advance_digest_to_done() -> None:
    run = _make_run(current_step=PipelineStep.DIGEST)
    run.advance_to_step(PipelineStep.DONE)
    assert run.current_step == PipelineStep.DONE


def test_advance_backward_collect_from_analyze_raises() -> None:
    run = _make_run(current_step=PipelineStep.ANALYZE)
    with pytest.raises(InvalidPipelineTransitionError):
        run.advance_to_step(PipelineStep.COLLECT)


def test_advance_backward_from_done_raises() -> None:
    run = _make_run(current_step=PipelineStep.DONE)
    with pytest.raises(InvalidPipelineTransitionError):
        run.advance_to_step(PipelineStep.ANALYZE)


def test_advance_to_same_step_raises() -> None:
    run = _make_run(current_step=PipelineStep.COLLECT)
    with pytest.raises(InvalidPipelineTransitionError):
        run.advance_to_step(PipelineStep.COLLECT)


def test_advance_can_skip_steps() -> None:
    run = _make_run(current_step=PipelineStep.COLLECT)
    run.advance_to_step(PipelineStep.DONE)
    assert run.current_step == PipelineStep.DONE


# ---------------------------------------------------------------------------
# Progress auto-calculation from step
# ---------------------------------------------------------------------------


def test_advance_to_analyze_sets_progress_050() -> None:
    run = _make_run(current_step=PipelineStep.COLLECT)
    run.advance_to_step(PipelineStep.ANALYZE)
    assert run.progress == 0.50


def test_advance_to_match_sets_progress_075() -> None:
    run = _make_run(current_step=PipelineStep.ANALYZE)
    run.advance_to_step(PipelineStep.MATCH)
    assert run.progress == 0.75


def test_advance_to_digest_sets_progress_100() -> None:
    run = _make_run(current_step=PipelineStep.MATCH)
    run.advance_to_step(PipelineStep.DIGEST)
    assert run.progress == 1.0


def test_advance_to_done_sets_progress_100() -> None:
    run = _make_run(current_step=PipelineStep.DIGEST)
    run.advance_to_step(PipelineStep.DONE)
    assert run.progress == 1.0


def test_advance_skip_sets_correct_progress() -> None:
    run = _make_run(current_step=PipelineStep.COLLECT)
    run.advance_to_step(PipelineStep.DONE)
    assert run.progress == 1.0


# ---------------------------------------------------------------------------
# record_step_outcome()
# ---------------------------------------------------------------------------


def test_record_step_outcome_stores_outcome() -> None:
    run = _make_run()
    run.record_step_outcome(PipelineStep.DIGEST, StepOutcome.SKIPPED)
    assert run.step_outcomes[PipelineStep.DIGEST] == StepOutcome.SKIPPED


def test_record_step_outcome_executed() -> None:
    run = _make_run()
    run.record_step_outcome(PipelineStep.DIGEST, StepOutcome.EXECUTED)
    assert run.step_outcomes[PipelineStep.DIGEST] == StepOutcome.EXECUTED


def test_record_step_outcome_overwrites_previous() -> None:
    run = _make_run()
    run.record_step_outcome(PipelineStep.DIGEST, StepOutcome.SKIPPED)
    run.record_step_outcome(PipelineStep.DIGEST, StepOutcome.EXECUTED)
    assert run.step_outcomes[PipelineStep.DIGEST] == StepOutcome.EXECUTED


def test_step_outcomes_empty_by_default() -> None:
    run = _make_run()
    assert run.step_outcomes == {}
