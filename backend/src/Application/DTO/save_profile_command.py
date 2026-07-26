from dataclasses import dataclass
from typing import Optional

from src.Application.DTO.authenticated_identity import AuthenticatedIdentity
from src.Application.DTO.cv_profile import CVProfile


@dataclass(frozen=True)
class SaveProfileCommand:
    """User-confirmed profile ready for embedding and persistence."""

    cv_profile: CVProfile
    cv_raw_text: str
    identity: Optional[AuthenticatedIdentity] = None
