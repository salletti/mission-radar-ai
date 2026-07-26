from dataclasses import dataclass

from src.Application.DTO.cv_profile import CVProfile


@dataclass(frozen=True)
class CVProfileDraft:
    """Output of ProcessCV — extracted profile plus raw CV text for the confirm step."""

    profile: CVProfile
    cv_raw_text: str
