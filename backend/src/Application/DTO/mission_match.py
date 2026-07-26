from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class MissionMatch:
    """Output DTO from MatchMissions — plain data transfer, not the Domain entity."""

    id: UUID
    user_profile_id: UUID
    analyzed_post_id: UUID
    semantic_score: float
    stack_score: float
    contract_score: float
    tjm_score: float
    remote_score: float
    global_score: float
