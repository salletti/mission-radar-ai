from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class MatchMissionsCommand:
    user_profile_id: UUID
