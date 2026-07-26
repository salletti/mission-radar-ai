"""Unit tests for dispatch_collection — no DB, no RabbitMQ, no Celery broker."""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.ValueObject.pipeline_enums import (
    PipelineStatus,
    PipelineStep,
    PipelineTrigger,
    PipelineType,
)
from src.Infrastructure.Persistence.exceptions import DatabaseError
from src.Infrastructure.Worker.scheduler.dispatch_collection import _fetch_and_dispatch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_query(query_text: str, limit: int = 50, user_profile_id=None) -> MagicMock:
    q = MagicMock()
    q.id = uuid4()
    q.query = query_text
    q.limit = limit
    q.user_profile_id = user_profile_id or uuid4()
    q.source = "linkedin"
    return q


def _make_pending_run(user_id) -> PipelineRun:
    return PipelineRun(
        user_id=user_id,
        pipeline_type=PipelineType.MISSION_REFRESH,
        trigger_type=PipelineTrigger.SCHEDULER,
        status=PipelineStatus.PENDING,
        current_step=PipelineStep.COLLECT,
        progress=0.0,
    )


def _make_session_ctx() -> MagicMock:
    """Renvoie un mock AsyncSessionLocal compatible avec `async with` + await commit()."""
    session = MagicMock()
    session.commit = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=ctx)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_queries_does_not_dispatch() -> None:
    """Aucune SearchQuery en base → StartMissionRefresh jamais appelé."""
    fake_repo = MagicMock()
    fake_repo.get_by_source = AsyncMock(return_value=[])

    with patch(
        "src.Infrastructure.Worker.scheduler.dispatch_collection.AsyncSessionLocal",
        _make_session_ctx(),
    ), patch(
        "src.Infrastructure.Worker.scheduler.dispatch_collection.SqlAlchemySearchQueryRepository",
        return_value=fake_repo,
    ), patch(
        "src.Infrastructure.Worker.scheduler.dispatch_collection.StartMissionRefresh"
    ) as MockUseCase:
        await _fetch_and_dispatch()

    MockUseCase.assert_not_called()


@pytest.mark.asyncio
async def test_single_query_dispatches_once_per_user() -> None:
    """Une SearchQuery → StartMissionRefresh.execute() appelé une fois pour cet utilisateur."""
    user_id = uuid4()
    query = _make_query("python freelance paris", limit=30, user_profile_id=user_id)
    fake_repo = MagicMock()
    fake_repo.get_by_source = AsyncMock(return_value=[query])

    mock_run = _make_pending_run(user_id)
    mock_use_case = MagicMock()
    mock_use_case.execute = AsyncMock(return_value=mock_run)

    with patch(
        "src.Infrastructure.Worker.scheduler.dispatch_collection.AsyncSessionLocal",
        _make_session_ctx(),
    ), patch(
        "src.Infrastructure.Worker.scheduler.dispatch_collection.SqlAlchemySearchQueryRepository",
        return_value=fake_repo,
    ), patch(
        "src.Infrastructure.Worker.scheduler.dispatch_collection.StartMissionRefresh",
        return_value=mock_use_case,
    ):
        await _fetch_and_dispatch()

    mock_use_case.execute.assert_called_once_with(user_id, PipelineTrigger.SCHEDULER)


@pytest.mark.asyncio
async def test_multiple_queries_same_user_dispatches_once() -> None:
    """N SearchQueries pour le même user → StartMissionRefresh.execute() appelé une seule fois."""
    user_id = uuid4()
    queries = [
        _make_query("python freelance paris", limit=50, user_profile_id=user_id),
        _make_query("ai engineer remote france", limit=40, user_profile_id=user_id),
    ]
    fake_repo = MagicMock()
    fake_repo.get_by_source = AsyncMock(return_value=queries)

    mock_run = _make_pending_run(user_id)
    mock_use_case = MagicMock()
    mock_use_case.execute = AsyncMock(return_value=mock_run)

    with patch(
        "src.Infrastructure.Worker.scheduler.dispatch_collection.AsyncSessionLocal",
        _make_session_ctx(),
    ), patch(
        "src.Infrastructure.Worker.scheduler.dispatch_collection.SqlAlchemySearchQueryRepository",
        return_value=fake_repo,
    ), patch(
        "src.Infrastructure.Worker.scheduler.dispatch_collection.StartMissionRefresh",
        return_value=mock_use_case,
    ):
        await _fetch_and_dispatch()

    assert mock_use_case.execute.call_count == 1


@pytest.mark.asyncio
async def test_multiple_users_dispatch_one_pipeline_each() -> None:
    """N SearchQueries pour N users distincts → StartMissionRefresh.execute() appelé N fois."""
    user_id_1 = uuid4()
    user_id_2 = uuid4()
    queries = [
        _make_query("python freelance paris", limit=50, user_profile_id=user_id_1),
        _make_query("ai engineer remote france", limit=40, user_profile_id=user_id_2),
    ]
    fake_repo = MagicMock()
    fake_repo.get_by_source = AsyncMock(return_value=queries)

    mock_run_1 = _make_pending_run(user_id_1)
    mock_run_2 = _make_pending_run(user_id_2)
    mock_use_case = MagicMock()
    mock_use_case.execute = AsyncMock(side_effect=[mock_run_1, mock_run_2])

    with patch(
        "src.Infrastructure.Worker.scheduler.dispatch_collection.AsyncSessionLocal",
        _make_session_ctx(),
    ), patch(
        "src.Infrastructure.Worker.scheduler.dispatch_collection.SqlAlchemySearchQueryRepository",
        return_value=fake_repo,
    ), patch(
        "src.Infrastructure.Worker.scheduler.dispatch_collection.StartMissionRefresh",
        return_value=mock_use_case,
    ):
        await _fetch_and_dispatch()

    assert mock_use_case.execute.call_count == 2
    called_user_ids = {call.args[0] for call in mock_use_case.execute.call_args_list}
    assert called_user_ids == {user_id_1, user_id_2}


@pytest.mark.asyncio
async def test_db_error_propagates() -> None:
    """Erreur DB → DatabaseError propagée depuis _fetch_and_dispatch().

    DynamicCollectionScheduler l'attrape dans apply_entry() pour protéger Beat.
    """
    fake_repo = MagicMock()
    fake_repo.get_by_source = AsyncMock(side_effect=DatabaseError("connection lost"))

    with patch(
        "src.Infrastructure.Worker.scheduler.dispatch_collection.AsyncSessionLocal",
        _make_session_ctx(),
    ), patch(
        "src.Infrastructure.Worker.scheduler.dispatch_collection.SqlAlchemySearchQueryRepository",
        return_value=fake_repo,
    ):
        with pytest.raises(DatabaseError, match="connection lost"):
            await _fetch_and_dispatch()
