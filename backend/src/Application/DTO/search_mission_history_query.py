from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class SearchMissionHistoryQuery:
    user_profile_id: UUID
    keyword: Optional[str] = None
    min_score: float = 0.0
    limit: int = 50
    offset: int = 0
