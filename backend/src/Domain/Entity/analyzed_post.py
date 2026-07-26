from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.Domain.Exception.domain_exceptions import EmptyAnalysisSummaryError
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode


@dataclass
class AnalyzedPost:
    """Normalized mission post — persisted after MissionNormalizer processing."""

    raw_post_id: UUID
    summary: str
    detected_stack: tuple[str, ...] = field(default_factory=tuple)
    detected_contract_type: ContractType = ContractType.UNKNOWN
    detected_remote_mode: RemoteMode = RemoteMode.UNKNOWN
    title: str | None = None
    company: str | None = None
    location: str | None = None
    seniority: str | None = None
    detected_tjm: float | None = None
    embedding: list[float] | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise EmptyAnalysisSummaryError("summary cannot be empty")
