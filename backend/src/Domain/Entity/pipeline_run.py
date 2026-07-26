from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.Domain.Exception.domain_exceptions import InvalidPipelineTransitionError
from src.Domain.ValueObject.pipeline_enums import (
    PipelineStatus,
    PipelineStep,
    PipelineTrigger,
    PipelineType,
    StepOutcome,
)

_STEP_ORDER = [
    PipelineStep.COLLECT,
    PipelineStep.ANALYZE,
    PipelineStep.MATCH,
    PipelineStep.DIGEST,
    PipelineStep.DONE,
]

_STEP_PROGRESS: dict[PipelineStep, float] = {
    PipelineStep.COLLECT: 0.25,
    PipelineStep.ANALYZE: 0.50,
    PipelineStep.MATCH: 0.75,
    PipelineStep.DIGEST: 1.0,
    PipelineStep.DONE: 1.0,
}


@dataclass
class PipelineRun:
    """Tracks the lifecycle of a single mission refresh pipeline execution."""

    user_id: UUID
    pipeline_type: PipelineType
    trigger_type: PipelineTrigger
    status: PipelineStatus
    current_step: PipelineStep
    progress: float
    id: UUID = field(default_factory=uuid4)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error_message: str | None = None
    step_outcomes: dict[PipelineStep, StepOutcome] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def start(self) -> None:
        if self.status != PipelineStatus.PENDING:
            raise InvalidPipelineTransitionError(
                f"Cannot start pipeline in status {self.status!r} — expected PENDING"
            )
        self.status = PipelineStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)
        self.progress = _STEP_PROGRESS[self.current_step]

    def complete(self) -> None:
        if self.status != PipelineStatus.RUNNING:
            raise InvalidPipelineTransitionError(
                f"Cannot complete pipeline in status {self.status!r} — expected RUNNING"
            )
        self.status = PipelineStatus.COMPLETED
        self.progress = 1.0
        self.finished_at = datetime.now(timezone.utc)

    def fail(self, error_message: str) -> None:
        if self.status != PipelineStatus.RUNNING:
            raise InvalidPipelineTransitionError(
                f"Cannot fail pipeline in status {self.status!r} — expected RUNNING"
            )
        self.status = PipelineStatus.FAILED
        self.error_message = error_message
        self.finished_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        if self.status != PipelineStatus.RUNNING:
            raise InvalidPipelineTransitionError(
                f"Cannot cancel pipeline in status {self.status!r} — expected RUNNING"
            )
        self.status = PipelineStatus.CANCELLED
        self.finished_at = datetime.now(timezone.utc)

    def record_step_outcome(self, step: PipelineStep, outcome: StepOutcome) -> None:
        self.step_outcomes[step] = outcome

    def advance_to_step(self, step: PipelineStep) -> None:
        current_index = _STEP_ORDER.index(self.current_step)
        target_index = _STEP_ORDER.index(step)
        if target_index <= current_index:
            raise InvalidPipelineTransitionError(
                f"Cannot advance from step {self.current_step!r} to {step!r} — must go forward"
            )
        self.current_step = step
        self.progress = _STEP_PROGRESS[step]
