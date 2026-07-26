from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetMissionHistoryQuery:
    user_profile_id: UUID
    min_score: float = 0.0
    limit: int = 50
    offset: int = 0
