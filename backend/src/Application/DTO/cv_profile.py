from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class CVProfile:
    """Output DTO from ProcessCV and LLMGateway."""

    email: str
    full_name: str
    title: str
    years_experience: int
    preferred_contract_type: str
    target_tjm: float
    preferred_remote_mode: str
    skills: tuple[str, ...]
    availability: datetime
    location: Optional[str] = None
