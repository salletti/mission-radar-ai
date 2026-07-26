from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.Domain.ValueObject.match_score import MatchScore


@dataclass
class MissionMatch:
    """Snapshot of the match between a user profile and an analyzed mission at a given instant.

    Stores the MatchScore VO produced by MissionMatchScorer — never recomputes it.
    """

    user_profile_id: UUID
    analyzed_post_id: UUID
    match_score: MatchScore
    created_at: datetime
    id: UUID = field(default_factory=uuid4)

    @classmethod
    def create(
        cls,
        user_profile_id: UUID,
        analyzed_post_id: UUID,
        match_score: MatchScore,
    ) -> "MissionMatch":
        return cls(
            user_profile_id=user_profile_id,
            analyzed_post_id=analyzed_post_id,
            match_score=match_score,
            created_at=datetime.now(timezone.utc),
        )

    @property
    def final_score(self) -> float:
        return self.match_score.final_score
