from datetime import date, datetime, timezone
from uuid import UUID

from src.Application.DTO.dashboard_summary import DashboardKpis, DashboardSummary, PipelineHealth
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.pipeline_run_repository import PipelineRunRepository
from src.Domain.ValueObject.pipeline_enums import PipelineStatus

_HEALTH_OK = "OK"
_HEALTH_DEGRADED = "DEGRADED"
_HEALTH_UNKNOWN = "UNKNOWN"


class GetDashboardSummary:
    """Builds the DashboardSummary cockpit model from MissionMatches and the latest PipelineRun."""

    def __init__(
        self,
        mission_match_repository: MissionMatchRepository,
        pipeline_run_repository: PipelineRunRepository,
    ) -> None:
        self._mission_match_repository = mission_match_repository
        self._pipeline_run_repository = pipeline_run_repository

    async def execute(self, user_profile_id: UUID) -> DashboardSummary:
        matches = await self._mission_match_repository.get_by_user(user_profile_id)
        latest_run = await self._pipeline_run_repository.find_latest_for_user(user_profile_id)

        today = datetime.now(timezone.utc).date()
        scores = [m.final_score for m in matches]
        new_today = sum(1 for m in matches if _to_utc_date(m.created_at) == today)
        average_score = round(sum(scores) / len(scores) * 100) if scores else 0
        total_missions = len(matches)

        kpis = DashboardKpis(
            total_missions=total_missions,
            new_today=new_today,
            average_score=average_score,
            last_refresh=_last_refresh(latest_run),
            pipeline_status=latest_run.status.value if latest_run else None,
        )
        health = PipelineHealth(
            status=_health_status(latest_run),
            last_pipeline_duration_seconds=_duration_seconds(latest_run),
        )
        return DashboardSummary(kpis=kpis, health=health)


def _to_utc_date(dt: datetime) -> date:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


def _last_refresh(run) -> datetime | None:
    if run and run.status == PipelineStatus.COMPLETED and run.finished_at:
        return run.finished_at
    return None


def _health_status(run) -> str:
    if run is None:
        return _HEALTH_UNKNOWN
    if run.status == PipelineStatus.COMPLETED:
        return _HEALTH_OK
    if run.status == PipelineStatus.FAILED:
        return _HEALTH_DEGRADED
    return _HEALTH_UNKNOWN


def _duration_seconds(run) -> float | None:
    if (
        run
        and run.status == PipelineStatus.COMPLETED
        and run.started_at
        and run.finished_at
    ):
        return (run.finished_at - run.started_at).total_seconds()
    return None
