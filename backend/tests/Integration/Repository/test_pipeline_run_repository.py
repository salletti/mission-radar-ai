"""Integration tests for SqlAlchemyPipelineRunRepository — requires running PostgreSQL."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.ValueObject.pipeline_enums import (
    PipelineStatus,
    PipelineStep,
    PipelineTrigger,
    PipelineType,
)
from src.Infrastructure.Persistence.Repository.pipeline_run_repository import SqlAlchemyPipelineRunRepository
from src.Infrastructure.Persistence.Repository.user_profile_repository import SqlAlchemyUserProfileRepository
from tests.Integration.Repository.conftest import make_user_profile

_NOW = datetime.now(timezone.utc)


async def _save_user_and_get_id(session: AsyncSession) -> object:
    """Persist a UserProfile to satisfy the FK constraint."""
    profile = make_user_profile()
    repo = SqlAlchemyUserProfileRepository(session)
    await repo.save(profile)
    await session.flush()
    return profile.id


def _make_run(user_id, **kwargs) -> PipelineRun:
    defaults = dict(
        user_id=user_id,
        pipeline_type=PipelineType.MISSION_REFRESH,
        trigger_type=PipelineTrigger.USER,
        status=PipelineStatus.PENDING,
        current_step=PipelineStep.COLLECT,
        progress=0.0,
    )
    return PipelineRun(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# save + get_by_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_save_and_get_by_id_round_trips_all_fields(db_session: AsyncSession) -> None:
    user_id = await _save_user_and_get_id(db_session)
    repo = SqlAlchemyPipelineRunRepository(db_session)
    run = _make_run(user_id)

    await repo.save(run)
    fetched = await repo.get_by_id(run.id)

    assert fetched is not None
    assert fetched.id == run.id
    assert fetched.user_id == user_id
    assert fetched.pipeline_type == PipelineType.MISSION_REFRESH
    assert fetched.trigger_type == PipelineTrigger.USER
    assert fetched.status == PipelineStatus.PENDING
    assert fetched.current_step == PipelineStep.COLLECT
    assert fetched.progress == 0.0


@pytest.mark.asyncio
async def test_save_with_nullable_fields_none(db_session: AsyncSession) -> None:
    user_id = await _save_user_and_get_id(db_session)
    repo = SqlAlchemyPipelineRunRepository(db_session)
    run = _make_run(user_id)

    await repo.save(run)
    fetched = await repo.get_by_id(run.id)

    assert fetched is not None
    assert fetched.started_at is None
    assert fetched.finished_at is None
    assert fetched.error_message is None


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_unknown_id(db_session: AsyncSession) -> None:
    repo = SqlAlchemyPipelineRunRepository(db_session)
    result = await repo.get_by_id(uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# find_latest_for_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_latest_for_user_returns_most_recent(db_session: AsyncSession) -> None:
    from datetime import timedelta
    user_id = await _save_user_and_get_id(db_session)
    repo = SqlAlchemyPipelineRunRepository(db_session)

    older = _make_run(user_id, created_at=_NOW - timedelta(hours=2))
    newer = _make_run(user_id, created_at=_NOW)
    await repo.save(older)
    await repo.save(newer)

    result = await repo.find_latest_for_user(user_id)
    assert result is not None
    assert result.id == newer.id


@pytest.mark.asyncio
async def test_find_latest_for_user_returns_none_when_no_runs(db_session: AsyncSession) -> None:
    repo = SqlAlchemyPipelineRunRepository(db_session)
    result = await repo.find_latest_for_user(uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# find_running_for_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_running_for_user_returns_active_run(db_session: AsyncSession) -> None:
    user_id = await _save_user_and_get_id(db_session)
    repo = SqlAlchemyPipelineRunRepository(db_session)

    running_run = _make_run(user_id, status=PipelineStatus.RUNNING)
    completed_run = _make_run(user_id, status=PipelineStatus.COMPLETED)
    await repo.save(running_run)
    await repo.save(completed_run)

    result = await repo.find_running_for_user(user_id)
    assert result is not None
    assert result.id == running_run.id
    assert result.status == PipelineStatus.RUNNING


@pytest.mark.asyncio
async def test_find_running_for_user_returns_none_when_no_running(db_session: AsyncSession) -> None:
    user_id = await _save_user_and_get_id(db_session)
    repo = SqlAlchemyPipelineRunRepository(db_session)

    completed = _make_run(user_id, status=PipelineStatus.COMPLETED)
    failed = _make_run(user_id, status=PipelineStatus.FAILED)
    await repo.save(completed)
    await repo.save(failed)

    result = await repo.find_running_for_user(user_id)
    assert result is None


@pytest.mark.asyncio
async def test_find_running_for_user_returns_none_with_no_runs(db_session: AsyncSession) -> None:
    repo = SqlAlchemyPipelineRunRepository(db_session)
    result = await repo.find_running_for_user(uuid4())
    assert result is None


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_persists_status_change(db_session: AsyncSession) -> None:
    user_id = await _save_user_and_get_id(db_session)
    repo = SqlAlchemyPipelineRunRepository(db_session)
    run = _make_run(user_id, status=PipelineStatus.PENDING)
    await repo.save(run)

    run.start()
    await repo.update(run)

    fetched = await repo.get_by_id(run.id)
    assert fetched is not None
    assert fetched.status == PipelineStatus.RUNNING
    assert fetched.started_at is not None


@pytest.mark.asyncio
async def test_update_persists_step_and_progress(db_session: AsyncSession) -> None:
    user_id = await _save_user_and_get_id(db_session)
    repo = SqlAlchemyPipelineRunRepository(db_session)
    run = _make_run(user_id, status=PipelineStatus.RUNNING)
    await repo.save(run)

    run.advance_to_step(PipelineStep.ANALYZE)  # progress auto-set to 0.50
    await repo.update(run)

    fetched = await repo.get_by_id(run.id)
    assert fetched is not None
    assert fetched.current_step == PipelineStep.ANALYZE
    assert fetched.progress == pytest.approx(0.50)


@pytest.mark.asyncio
async def test_update_persists_error_message(db_session: AsyncSession) -> None:
    user_id = await _save_user_and_get_id(db_session)
    repo = SqlAlchemyPipelineRunRepository(db_session)
    run = _make_run(user_id, status=PipelineStatus.RUNNING)
    await repo.save(run)

    run.fail("LLM timeout")
    await repo.update(run)

    fetched = await repo.get_by_id(run.id)
    assert fetched is not None
    assert fetched.status == PipelineStatus.FAILED
    assert fetched.error_message == "LLM timeout"
    assert fetched.finished_at is not None
