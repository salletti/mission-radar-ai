from dataclasses import dataclass

from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.ValueObject.match_score import MatchScore


@dataclass(frozen=True)
class MatchMissionResult:
    """Result of matching one analyzed mission against a user profile."""

    mission: AnalyzedPost
    match_score: MatchScore
