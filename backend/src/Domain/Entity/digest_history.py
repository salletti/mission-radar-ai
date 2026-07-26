from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class DigestStatus(str, Enum):
    SENT = "sent"
    FAILED = "failed"


@dataclass
class DigestHistory:
    """Represents a real Daily Digest send attempt. Created by the Worker only, never by the API."""

    user_id: UUID
    pipeline_run_id: UUID | None
    sent_at: datetime
    status: DigestStatus
    missions_count: int
    id: UUID = field(default_factory=uuid4)
    provider_message_id: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
