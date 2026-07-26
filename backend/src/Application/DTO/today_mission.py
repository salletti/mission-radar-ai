from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class TodayMission:
    """Output DTO from GetTodayMissions — mission details enriched with match scores."""

    mission_match_id: UUID
    analyzed_post_id: UUID
    raw_post_id: UUID
    author_name: str
    content_excerpt: str
    post_url: str
    detected_stack: tuple[str, ...]
    detected_contract_type: str
    detected_remote_mode: str
    global_score: float
    score_details: dict[str, float]
    detected_tjm: Optional[float] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
