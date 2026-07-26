from __future__ import annotations

import re
from uuid import UUID

from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.ValueObject.post_analysis import PostAnalysis
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode

_CONTRACT_MAP: dict[str, ContractType] = {
    "freelance": ContractType.FREELANCE,
    "indépendant": ContractType.FREELANCE,
    "independant": ContractType.FREELANCE,
    "portage": ContractType.FREELANCE,
    "mission": ContractType.FREELANCE,
    "cdi": ContractType.PERMANENT,
    "permanent": ContractType.PERMANENT,
    "salarié": ContractType.PERMANENT,
    "salarie": ContractType.PERMANENT,
    "cdd": ContractType.FIXED_TERM,
    "fixed_term": ContractType.FIXED_TERM,
    "stage": ContractType.INTERNSHIP,
    "internship": ContractType.INTERNSHIP,
    "alternance": ContractType.APPRENTICESHIP,
    "apprenticeship": ContractType.APPRENTICESHIP,
}

_REMOTE_MAP: dict[str, RemoteMode] = {
    "full_remote": RemoteMode.FULL_REMOTE,
    "full remote": RemoteMode.FULL_REMOTE,
    "100% remote": RemoteMode.FULL_REMOTE,
    "100% télétravail": RemoteMode.FULL_REMOTE,
    "100% teletravail": RemoteMode.FULL_REMOTE,
    "télétravail total": RemoteMode.FULL_REMOTE,
    "teletravail total": RemoteMode.FULL_REMOTE,
    "entièrement à distance": RemoteMode.FULL_REMOTE,
    "entierement a distance": RemoteMode.FULL_REMOTE,
    "remote": RemoteMode.FULL_REMOTE,
    "hybrid": RemoteMode.HYBRID,
    "hybride": RemoteMode.HYBRID,
    "télétravail partiel": RemoteMode.HYBRID,
    "teletravail partiel": RemoteMode.HYBRID,
    "présentiel": RemoteMode.ONSITE,
    "presentiel": RemoteMode.ONSITE,
    "onsite": RemoteMode.ONSITE,
    "on-site": RemoteMode.ONSITE,
    "sur site": RemoteMode.ONSITE,
    "100% présentiel": RemoteMode.ONSITE,
    "100% presentiel": RemoteMode.ONSITE,
}

# Matches: "650", "650.0", "650,0" — optionally followed by non-digit chars
_TJM_RANGE_RE = re.compile(r"(\d[\d\s]*(?:[.,]\d+)?)\s*[-–]\s*(\d[\d\s]*(?:[.,]\d+)?)")
_TJM_SINGLE_RE = re.compile(r"(\d[\d\s]*(?:[.,]\d+)?)")


class MissionNormalizer:
    """Pure domain service — no I/O, no DB access, no Infrastructure imports.

    Transforms a raw PostAnalysis (LLM output) into a normalized AnalyzedPost
    ready for persistence. Called only when is_job_offer is True.
    """

    def normalize(self, raw_post_id: UUID, analysis: PostAnalysis) -> AnalyzedPost:
        return AnalyzedPost(
            raw_post_id=raw_post_id,
            summary=analysis.summary,
            detected_stack=self._merge_stack(analysis.required_skills, analysis.nice_to_have_skills),
            detected_contract_type=self._normalize_contract_type(analysis.contract_type),
            detected_remote_mode=self._normalize_remote_mode(analysis.remote_policy),
            title=analysis.title,
            company=analysis.company,
            location=analysis.location,
            seniority=analysis.seniority,
            detected_tjm=self._parse_tjm(analysis.daily_rate),
        )

    def _merge_stack(
        self,
        required: tuple[str, ...],
        nice_to_have: tuple[str, ...],
    ) -> tuple[str, ...]:
        merged = {t.lower().strip() for t in (*required, *nice_to_have) if t.strip()}
        return tuple(sorted(merged))

    def _parse_tjm(self, daily_rate: str | None) -> float | None:
        if not daily_rate:
            return None
        cleaned = daily_rate.replace(" ", "").replace("\xa0", "")
        # Range pattern: "600-700€" → average
        m_range = _TJM_RANGE_RE.search(cleaned)
        if m_range:
            lo = float(m_range.group(1).replace(" ", "").replace(",", "."))
            hi = float(m_range.group(2).replace(" ", "").replace(",", "."))
            return (lo + hi) / 2
        # Single value: "650€/j", "TJM 650", "env. 650€"
        m = _TJM_SINGLE_RE.search(cleaned)
        if m:
            return float(m.group(1).replace(" ", "").replace(",", "."))
        return None

    def _normalize_contract_type(self, raw: str | None) -> ContractType:
        if not raw:
            return ContractType.UNKNOWN
        normalized = raw.lower().strip()
        for key, contract_type in _CONTRACT_MAP.items():
            if key in normalized:
                return contract_type
        return ContractType.UNKNOWN

    def _normalize_remote_mode(self, raw: str | None) -> RemoteMode:
        if not raw:
            return RemoteMode.UNKNOWN
        normalized = raw.lower().strip()
        # Exact match first (longer keys take priority via iteration order above)
        if normalized in _REMOTE_MAP:
            return _REMOTE_MAP[normalized]
        # Substring match
        for key, mode in _REMOTE_MAP.items():
            if key in normalized:
                return mode
        return RemoteMode.UNKNOWN
