from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class UserProfile:
    """Output DTO from GetUserProfile — flattened, wire-friendly view of the profile."""

    id: UUID
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
