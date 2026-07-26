from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ScoreBreakdown:
    """Numeric breakdown of the matching score by dimension.

    Fields are populated only when the corresponding scoring engine is active.
    Null values indicate dimensions not yet computed — the contract is stable
    and will be enriched progressively without breaking callers.
    """

    skills: Optional[float] = None
    experience: Optional[float] = None
    location: Optional[float] = None
    contract: Optional[float] = None
    daily_rate: Optional[float] = None


@dataclass(frozen=True)
class ExplainabilityReport:
    """Structured explanation of why a mission was matched.

    Designed for progressive enrichment: every field can start empty/null
    and be populated by future matching engine iterations without changing
    the API contract, DTOs, or frontend components.
    """

    score_breakdown: ScoreBreakdown
    matching_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    strong_points: tuple[str, ...]
    missing_skills: tuple[str, ...]
    recommendations: tuple[str, ...]
