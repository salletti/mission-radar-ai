from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class ActivityEvent:
    type: Literal["MISSION_MATCH", "DAILY_DIGEST"]
    occurred_at: datetime
    title: str
    description: str
    score: int  # MISSION_MATCH: 0-100%; DAILY_DIGEST: missions_count (>=0=SENT, -1=FAILED)
    mission_match_id: UUID | None = None
    digest_history_id: UUID | None = None


@dataclass(frozen=True)
class ActivityHistoryPage:
    items: list[ActivityEvent]
    total: int
    limit: int
    offset: int
