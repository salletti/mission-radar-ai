"""Unit tests for GetDashboardSummary use case — no I/O, no DB."""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.UseCase.get_dashboard_summary import GetDashboardSummary
from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.pipeline_run_repository import PipelineRunRepository
from src.Domain.ValueObject.match_score import MatchScore
from src.Domain.ValueObject.pipeline_enums import PipelineStatus, PipelineStep, PipelineTrigger, PipelineType

_NOW = datetime.now(timezone.utc)
_USER_ID = uuid4()
_OTHER_USER_ID = uuid4()


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeMissionMatchRepository(MissionMatchRepository):
    def __init__(self, matches: Optional[list[MissionMatch]] = None) -> None:
        self._matches = matches or []

    async def get_by_user(self, user_id: UUID) -> list[MissionMatch]:
        return [m for m in self._matches if m.user_profile_id == user_id]

    async def save(self, match: MissionMatch) -> None: ...
    async def save_many(self, matches: list[MissionMatch]) -> None: ...
    async def get_by_id(self, match_id: UUID) -> Optional[MissionMatch]: return None
    async def get_by_post(self, post_id: UUID) -> list[MissionMatch]: return []
    async def get_best_matches(self, user_id: UUID, limit: int) -> list[MissionMatch]: return []
    async def delete_user_matches(self, user_id: UUID) -> None: ...


class FakePipelineRunRepository(PipelineRunRepository):
    def __init__(self, latest: Optional[PipelineRun] = None) -> None:
        self._latest = latest

    async def find_latest_for_user(self, user_id: UUID) -> Optional[PipelineRun]:
        return self._latest

    async def save(self, run: PipelineRun) -> None: ...
    async def get_by_id(self, run_id: UUID) -> Optional[PipelineRun]: return None
    async def find_running_for_user(self, user_id: UUID) -> Optional[PipelineRun]: return None
    async def update(self, run: PipelineRun) -> None: ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_match(score: float = 0.8, created_at: datetime = _NOW) -> MissionMatch:
    return MissionMatch(
        user_profile_id=_USER_ID,
        analyzed_post_id=uuid4(),
        match_score=MatchScore(semantic_score=score, contract_score=score, remote_score=score, tjm_score=score),
        created_at=created_at,
    )


def _make_pipeline(
    status: PipelineStatus = PipelineStatus.COMPLETED,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
) -> PipelineRun:
    return PipelineRun(
        user_id=_USER_ID,
        pipeline_type=PipelineType.MISSION_REFRESH,
        trigger_type=PipelineTrigger.USER,
        status=status,
        current_step=PipelineStep.DONE,
        progress=1.0,
        started_at=started_at or _NOW - timedelta(seconds=40),
        finished_at=finished_at if finished_at is not None else _NOW,
    )


def _use_case(matches=None, latest_run=None) -> GetDashboardSummary:
    return GetDashboardSummary(
        mission_match_repository=FakeMissionMatchRepository(matches),
        pipeline_run_repository=FakePipelineRunRepository(latest_run),
    )


# ---------------------------------------------------------------------------
# Tests — empty state
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_returns_zero_kpis_and_unknown_health():
    summary = await _use_case().execute(_USER_ID)
    assert summary.kpis.total_missions == 0
    assert summary.kpis.new_today == 0
    assert summary.kpis.average_score == 0
    assert summary.kpis.last_refresh is None
    assert summary.kpis.pipeline_status is None
    assert summary.health.status == "UNKNOWN"
    assert summary.health.last_pipeline_duration_seconds is None


# ---------------------------------------------------------------------------
# Tests — KPIs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_total_missions_counts_all_user_matches():
    matches = [_make_match() for _ in range(5)]
    summary = await _use_case(matches=matches).execute(_USER_ID)
    assert summary.kpis.total_missions == 5


@pytest.mark.asyncio
async def test_new_today_counts_only_todays_matches():
    today = datetime.now(timezone.utc)
    yesterday = today - timedelta(days=1)
    matches = [_make_match(created_at=today), _make_match(created_at=yesterday), _make_match(created_at=today)]
    summary = await _use_case(matches=matches).execute(_USER_ID)
    assert summary.kpis.new_today == 2


@pytest.mark.asyncio
async def test_average_score_is_integer_0_to_100():
    # score = 0.8 for all 4 components → final_score ≈ 0.8 → avg_score = 80
    matches = [_make_match(score=0.8), _make_match(score=0.8)]
    summary = await _use_case(matches=matches).execute(_USER_ID)
    assert 0 <= summary.kpis.average_score <= 100
    assert isinstance(summary.kpis.average_score, int)
    assert summary.kpis.average_score == 80


@pytest.mark.asyncio
async def test_user_isolation_only_counts_own_matches():
    own = _make_match()
    other = MissionMatch(
        user_profile_id=_OTHER_USER_ID,
        analyzed_post_id=uuid4(),
        match_score=MatchScore(semantic_score=0.9, contract_score=0.9, remote_score=0.9, tjm_score=0.9),
        created_at=_NOW,
    )
    summary = await _use_case(matches=[own, other]).execute(_USER_ID)
    assert summary.kpis.total_missions == 1


# ---------------------------------------------------------------------------
# Tests — Pipeline health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_completed_pipeline_sets_health_ok_and_last_refresh():
    run = _make_pipeline(status=PipelineStatus.COMPLETED)
    summary = await _use_case(latest_run=run).execute(_USER_ID)
    assert summary.health.status == "OK"
    assert summary.kpis.last_refresh == run.finished_at
    assert summary.kpis.pipeline_status == "completed"


@pytest.mark.asyncio
async def test_completed_pipeline_computes_duration():
    started = _NOW - timedelta(seconds=34)
    run = _make_pipeline(status=PipelineStatus.COMPLETED, started_at=started, finished_at=_NOW)
    summary = await _use_case(latest_run=run).execute(_USER_ID)
    assert summary.health.last_pipeline_duration_seconds == pytest.approx(34.0, abs=0.1)


@pytest.mark.asyncio
async def test_failed_pipeline_sets_health_degraded():
    run = _make_pipeline(status=PipelineStatus.FAILED)
    summary = await _use_case(latest_run=run).execute(_USER_ID)
    assert summary.health.status == "DEGRADED"
    assert summary.kpis.last_refresh is None
    assert summary.kpis.pipeline_status == "failed"


@pytest.mark.asyncio
async def test_running_pipeline_sets_health_unknown():
    run = _make_pipeline(status=PipelineStatus.RUNNING)
    run.finished_at = None  # simulate in-flight — no finished_at yet
    summary = await _use_case(latest_run=run).execute(_USER_ID)
    assert summary.health.status == "UNKNOWN"
    assert summary.kpis.last_refresh is None
    assert summary.kpis.pipeline_status == "running"


@pytest.mark.asyncio
async def test_no_pipeline_sets_unknown_and_no_duration():
    summary = await _use_case().execute(_USER_ID)
    assert summary.health.status == "UNKNOWN"
    assert summary.health.last_pipeline_duration_seconds is None
