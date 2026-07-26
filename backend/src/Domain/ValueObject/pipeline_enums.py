from enum import Enum


class PipelineType(str, Enum):
    MISSION_REFRESH = "mission_refresh"


class PipelineTrigger(str, Enum):
    USER = "user"
    SCHEDULER = "scheduler"
    SYSTEM = "system"


class PipelineStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStep(str, Enum):
    COLLECT = "collect"
    ANALYZE = "analyze"
    MATCH = "match"
    DIGEST = "digest"
    DONE = "done"


class StepOutcome(str, Enum):
    EXECUTED = "executed"
    SKIPPED = "skipped"
    FAILED = "failed"
