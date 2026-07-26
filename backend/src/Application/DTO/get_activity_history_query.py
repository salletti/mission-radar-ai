from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetActivityHistoryQuery:
    user_profile_id: UUID
    limit: int = 20
    offset: int = 0
