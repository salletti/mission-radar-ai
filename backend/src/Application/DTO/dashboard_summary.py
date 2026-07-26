from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DashboardKpis:
    """KPI metrics displayed in the Dashboard header."""

    total_missions: int
    new_today: int
    average_score: int  # 0–100
    last_refresh: datetime | None
    pipeline_status: str | None  # PipelineStatus enum value or None


@dataclass(frozen=True)
class PipelineHealth:
    """Pipeline health indicator."""

    status: str  # "OK" | "DEGRADED" | "UNKNOWN"
    last_pipeline_duration_seconds: float | None


@dataclass(frozen=True)
class DashboardSummary:
    """Presentation model for the Dashboard cockpit — extensible without breaking the API."""

    kpis: DashboardKpis
    health: PipelineHealth
