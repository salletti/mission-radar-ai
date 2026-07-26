import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from src.Domain.Exception.domain_exceptions import InvalidEmailError
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class UserProfile:
    """Represents the freelancer's profile used for mission matching."""

    email: str
    full_name: str
    title: str
    years_experience: int
    preferred_contract_type: ContractType
    target_tjm: float
    preferred_remote_mode: RemoteMode
    skills: Stack
    availability: datetime
    location: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    embedding: Optional[list[float]] = None
    cv_raw_text: Optional[str] = None

    def __post_init__(self) -> None:
        if not _EMAIL_RE.match(self.email):
            raise InvalidEmailError(f"Invalid email format: {self.email!r}")
