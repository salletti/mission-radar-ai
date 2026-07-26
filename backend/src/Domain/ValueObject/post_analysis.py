from __future__ import annotations

from dataclasses import dataclass

from src.Domain.Exception.domain_exceptions import EmptyAnalysisSummaryError


@dataclass(frozen=True)
class PostAnalysis:
    """Raw LLM analysis output for a RawPost — transient, not persisted.

    is_job_offer gates persistence: only True results are passed to MissionNormalizer.
    """

    summary: str
    required_skills: tuple[str, ...]
    nice_to_have_skills: tuple[str, ...]
    is_job_offer: bool = False
    title: str | None = None
    company: str | None = None
    location: str | None = None
    contract_type: str | None = None
    seniority: str | None = None
    remote_policy: str | None = None
    daily_rate: str | None = None

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise EmptyAnalysisSummaryError("summary cannot be empty")

    @classmethod
    def from_llm_payload(cls, payload: dict) -> PostAnalysis:
        def clean(val: str | None) -> str | None:
            if val is None:
                return None
            stripped = val.strip()
            return stripped if stripped else None

        def clean_list(val: list | None) -> tuple[str, ...]:
            if not val:
                return ()
            return tuple(s.strip() for s in val if isinstance(s, str) and s.strip())

        summary = clean(payload.get("summary")) or ""
        return cls(
            summary=summary,
            required_skills=clean_list(payload.get("required_skills")),
            nice_to_have_skills=clean_list(payload.get("nice_to_have_skills")),
            is_job_offer=bool(payload.get("is_job_offer", False)),
            title=clean(payload.get("title")),
            company=clean(payload.get("company")),
            location=clean(payload.get("location")),
            contract_type=clean(payload.get("contract_type")),
            seniority=clean(payload.get("seniority")),
            remote_policy=clean(payload.get("remote_policy")),
            daily_rate=clean(payload.get("daily_rate")),
        )
