from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.Application.DTO.explainability_report import ExplainabilityReport


@dataclass(frozen=True)
class MissionMatchDetail:
    """Full detail DTO for a single MissionMatch — used by the Dashboard detail endpoint."""

    mission_match_id: UUID
    analyzed_post_id: UUID
    raw_post_id: UUID
    author_name: str
    author_url: str
    content: str
    post_url: str
    published_at: datetime
    title: Optional[str]
    company: Optional[str]
    location: Optional[str]
    summary: str
    seniority: Optional[str]
    detected_stack: tuple[str, ...]
    detected_contract_type: str
    detected_remote_mode: str
    detected_tjm: Optional[float]
    global_score: float
    score_details: dict[str, float]
    matched_at: datetime
    matched_skills: tuple[str, ...]
    missing_skills: tuple[str, ...]
    explanation: ExplainabilityReport
