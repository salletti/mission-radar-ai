from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.Domain.ValueObject.digest_mission import DigestMission


@dataclass
class DigestEmail:
    """Business content of the daily digest — no HTML, no sending technology.

    Persisted in Phase 7.2 for audit trail and deduplication.
    """

    user_id: UUID
    user_email: str
    user_name: str
    subject: str
    missions: tuple[DigestMission, ...]
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: UUID = field(default_factory=uuid4)

    @property
    def mission_count(self) -> int:
        return len(self.missions)
