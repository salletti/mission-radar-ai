"""Unit tests for ProcessCV use case — no I/O, no DB, no external services."""
from datetime import datetime, timezone

import pytest

from src.Application.DTO.cv_profile import CVProfile
from src.Application.DTO.cv_profile_draft import CVProfileDraft
from src.Application.DTO.process_cv_command import ProcessCVCommand
from src.Application.Gateway.cv_extractor_gateway import CVExtractorGateway
from src.Application.Gateway.llm_gateway import LLMGateway
from src.Application.UseCase.process_cv import ProcessCV

_AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)

_FAKE_DTO = CVProfile(
    email="test@example.com",
    full_name="Ada Lovelace",
    title="Senior Python Engineer",
    years_experience=10,
    preferred_contract_type="freelance",
    target_tjm=700.0,
    preferred_remote_mode="full_remote",
    skills=("python", "fastapi"),
    availability=_AVAILABILITY,
    location="Paris",
)


# ---------------------------------------------------------------------------
# Fake implementations
# ---------------------------------------------------------------------------


class FakeCVExtractor(CVExtractorGateway):
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def extract_text(self, file_path: str) -> str:
        self.calls.append(file_path)
        return "fake cv text"


class FakeLLMGateway(LLMGateway):
    def __init__(self) -> None:
        self.extract_calls: list[str] = []

    async def extract_profile_from_cv(self, cv_text: str) -> CVProfile:
        self.extract_calls.append(cv_text)
        return _FAKE_DTO

    async def summarize_mission(self, content: str) -> str:
        return "summary"

    async def generate_search_queries(self, profile) -> list[dict]:
        return []

    async def analyze_post(self, raw_post) -> "PostAnalysis":  # type: ignore[override]
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_use_case(
    extractor: FakeCVExtractor | None = None,
    llm: FakeLLMGateway | None = None,
) -> tuple[ProcessCV, FakeCVExtractor, FakeLLMGateway]:
    extractor = extractor or FakeCVExtractor()
    llm = llm or FakeLLMGateway()
    return ProcessCV(extractor, llm), extractor, llm


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_process_cv_returns_cv_profile_draft() -> None:
    uc, _, _ = _make_use_case()

    result = await uc.execute(ProcessCVCommand(email="test@example.com", file_path="/cvs/ada.pdf"))

    assert isinstance(result, CVProfileDraft)
    assert isinstance(result.profile, CVProfile)


async def test_process_cv_includes_cv_raw_text() -> None:
    uc, _, _ = _make_use_case()

    result = await uc.execute(ProcessCVCommand(email="test@example.com", file_path="/cvs/ada.pdf"))

    assert result.cv_raw_text == "fake cv text"


async def test_process_cv_profile_contains_extracted_fields() -> None:
    uc, _, _ = _make_use_case()

    result = await uc.execute(ProcessCVCommand(email="test@example.com", file_path="/cvs/ada.pdf"))

    assert result.profile.full_name == "Ada Lovelace"
    assert result.profile.title == "Senior Python Engineer"
    assert result.profile.years_experience == 10
    assert result.profile.preferred_contract_type == "freelance"
    assert result.profile.target_tjm == 700.0
    assert "python" in result.profile.skills


async def test_process_cv_calls_extractor_with_correct_path() -> None:
    uc, extractor, _ = _make_use_case()

    await uc.execute(ProcessCVCommand(email="test@example.com", file_path="/cvs/ada.pdf"))

    assert extractor.calls == ["/cvs/ada.pdf"]


async def test_process_cv_calls_llm_with_extracted_text() -> None:
    uc, _, llm = _make_use_case()

    await uc.execute(ProcessCVCommand(email="test@example.com", file_path="/cvs/ada.pdf"))

    assert llm.extract_calls == ["fake cv text"]


async def test_process_cv_does_not_persist_anything() -> None:
    """ProcessCV must remain a pure extraction step — no side effects."""
    extractor = FakeCVExtractor()
    llm = FakeLLMGateway()
    uc = ProcessCV(cv_extractor=extractor, llm=llm)

    result = await uc.execute(ProcessCVCommand(email="test@example.com", file_path="/cvs/ada.pdf"))

    # Only extractor + LLM should be touched — no repository, no embedding
    assert len(extractor.calls) == 1
    assert len(llm.extract_calls) == 1
    assert isinstance(result, CVProfileDraft)
