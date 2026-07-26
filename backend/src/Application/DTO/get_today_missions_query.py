from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetTodayMissionsQuery:
    user_profile_id: UUID
    min_score: float = 0.5
    limit: int = 20
