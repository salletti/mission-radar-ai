from dataclasses import dataclass, field
from uuid import UUID

from src.Domain.ValueObject.remote_mode import RemoteMode


@dataclass(frozen=True)
class DigestMission:
    """Snapshot of a mission entry for the daily digest.

    Assembled by the Use Case (Phase 7.2) from MissionMatch + AnalyzedPost + RawPost.
    Pure value object — immutable, no persistence, no I/O.
    """

    mission_match_id: UUID
    analyzed_post_id: UUID
    final_score: float
    summary: str
    title: str | None = None
    company: str | None = None
    detected_stack: tuple[str, ...] = field(default_factory=tuple)
    detected_remote_mode: RemoteMode = RemoteMode.UNKNOWN
    detected_tjm: float | None = None
    post_url: str | None = None
