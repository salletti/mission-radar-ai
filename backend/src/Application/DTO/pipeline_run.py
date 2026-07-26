from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class PipelineRun:
    """Output DTO from GetPipelineStatus — flattened, wire-friendly view of the
    latest pipeline run for a user. Deliberately lighter than the Domain PipelineRun
    entity: no user_id/pipeline_type/trigger_type, not relevant to an MCP client."""

    id: UUID
    status: str
    current_step: str
    progress: float
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]
    step_outcomes: dict[str, str]
