from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetMissionDetailsQuery:
    mission_match_id: UUID
    user_profile_id: UUID
