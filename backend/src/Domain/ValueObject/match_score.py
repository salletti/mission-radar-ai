from dataclasses import dataclass

from src.Domain.Exception.domain_exceptions import InvalidScoreError

# V1 weights — stack scoring added in Phase 6 recalibration
_WEIGHTS = {
    "semantic_score": 0.70,
    "contract_score": 0.15,
    "remote_score": 0.10,
    "tjm_score": 0.05,
}


@dataclass(frozen=True)
class MatchScore:
    """Weighted match score between a mission post and the user profile.

    V1 formula (Phase 5.1.1): semantic 70%, contract 15%, remote 10%, TJM 5%.
    Weights are recalibratable in Phase 6.
    """

    semantic_score: float
    contract_score: float
    remote_score: float
    tjm_score: float

    def __post_init__(self) -> None:
        for name in _WEIGHTS:
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise InvalidScoreError(f"{name} must be between 0.0 and 1.0, got {value}")

    @property
    def final_score(self) -> float:
        return round(
            self.semantic_score * _WEIGHTS["semantic_score"]
            + self.contract_score * _WEIGHTS["contract_score"]
            + self.remote_score * _WEIGHTS["remote_score"]
            + self.tjm_score * _WEIGHTS["tjm_score"],
            4,
        )
