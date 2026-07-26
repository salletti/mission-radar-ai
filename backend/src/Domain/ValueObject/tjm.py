from dataclasses import dataclass

from src.Domain.Exception.domain_exceptions import InvalidTJMError


@dataclass(frozen=True)
class TJM:
    """Daily rate (Taux Journalier Moyen) for a freelance mission."""

    amount: float
    currency: str = "EUR"
    unit: str = "day"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise InvalidTJMError(f"TJM amount cannot be negative: {self.amount}")

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}/{self.unit}"
