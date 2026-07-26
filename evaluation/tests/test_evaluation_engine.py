"""Tests for EvaluationEngine — fakes in memory, no real LLM or DB."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.Application.Gateway.embedding_gateway import EmbeddingGateway
from src.Application.Gateway.llm_gateway import LLMGateway
from src.Domain.Entity.raw_post import RawPost
from src.Domain.ValueObject.post_analysis import PostAnalysis
from models.gold_sample import GoldSample
from runners.evaluation_engine import EvaluationEngine

_NOW = datetime(2026, 7, 5, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeLLMGateway(LLMGateway):
    def __init__(self, post_analysis: PostAnalysis) -> None:
        self._analysis = post_analysis

    async def analyze_post(self, raw_post: RawPost) -> PostAnalysis:
        return self._analysis

    async def extract_profile_from_cv(self, cv_text: str):  # type: ignore[override]
        raise NotImplementedError

    async def summarize_mission(self, content: str) -> str:  # type: ignore[override]
        raise NotImplementedError

    async def generate_search_queries(self, profile) -> list[dict]:  # type: ignore[override]
        raise NotImplementedError


class FakeEmbeddingGateway(EmbeddingGateway):
    async def embed_text(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    async def compute_similarity(self, a, b) -> float:  # type: ignore[override]
        return 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_raw_post(content: str = "Mission Python Senior freelance Paris hybrid 650€/j") -> RawPost:
    return RawPost(
        source="linkedin",
        external_id="urn:li:activity:1111111111111111111",
        author_name="Recruiter",
        author_url="",
        content=content,
        post_url="",
        published_at=_NOW,
        scraped_at=_NOW,
    )


def _make_sample(**kwargs) -> GoldSample:
    defaults = dict(
        raw_post_id="urn:li:activity:1111111111111111111",
        post_content="Mission Python Senior freelance Paris hybrid 650€/j",
        expected_company="Accenture",
        expected_title="Développeur Python Senior",
        expected_location="Paris, France",
        expected_contract="freelance",
        expected_remote="hybrid",
        expected_stack=["python", "fastapi"],
        expected_tjm=650.0,
        expected_salary=None,
    )
    defaults.update(kwargs)
    return GoldSample(**defaults)


def _make_analysis(**kwargs) -> PostAnalysis:
    defaults = dict(
        summary="Mission Python Senior freelance Paris hybrid 650€/j",
        required_skills=("python", "fastapi"),
        nice_to_have_skills=(),
        is_job_offer=True,
        title="Développeur Python Senior",
        company="Accenture",
        location="Paris, France",
        contract_type="freelance",
        remote_policy="hybrid",
        daily_rate="650",
    )
    defaults.update(kwargs)
    return PostAnalysis(**defaults)


# ---------------------------------------------------------------------------
# evaluate_sample — job offer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_sample_returns_evaluation_result() -> None:
    engine = EvaluationEngine(
        llm_gateway=FakeLLMGateway(_make_analysis()),
        embedding_gateway=FakeEmbeddingGateway(),
    )
    result = await engine.evaluate_sample(_make_sample(), _make_raw_post())
    assert result.sample_id == "urn:li:activity:1111111111111111111"


@pytest.mark.asyncio
async def test_evaluate_sample_perfect_extraction_all_correct() -> None:
    engine = EvaluationEngine(
        llm_gateway=FakeLLMGateway(_make_analysis()),
        embedding_gateway=FakeEmbeddingGateway(),
    )
    result = await engine.evaluate_sample(_make_sample(), _make_raw_post())
    assert result.contract.correct
    assert result.remote.correct
    assert result.company.correct
    assert result.stack.correct
    assert result.stack.missing == []


@pytest.mark.asyncio
async def test_evaluate_sample_stack_missing_detected() -> None:
    analysis = _make_analysis(required_skills=("python",), nice_to_have_skills=())
    sample = _make_sample(expected_stack=["python", "fastapi", "docker"])
    engine = EvaluationEngine(
        llm_gateway=FakeLLMGateway(analysis),
        embedding_gateway=FakeEmbeddingGateway(),
    )
    result = await engine.evaluate_sample(sample, _make_raw_post())
    assert not result.stack.correct
    assert "fastapi" in result.stack.missing
    assert "docker" in result.stack.missing


@pytest.mark.asyncio
async def test_evaluate_sample_wrong_contract_detected() -> None:
    analysis = _make_analysis(contract_type="permanent")
    sample = _make_sample(expected_contract="freelance")
    engine = EvaluationEngine(
        llm_gateway=FakeLLMGateway(analysis),
        embedding_gateway=FakeEmbeddingGateway(),
    )
    result = await engine.evaluate_sample(sample, _make_raw_post())
    assert not result.contract.correct


@pytest.mark.asyncio
async def test_evaluate_sample_embedding_is_generated() -> None:
    """Checks that the embedding gateway is called (AnalyzedPost.embedding is set)."""
    captured: list[str] = []

    class CapturingEmbeddingGateway(EmbeddingGateway):
        async def embed_text(self, text: str) -> list[float]:
            captured.append(text)
            return [0.1, 0.2, 0.3]

        async def compute_similarity(self, a, b) -> float:  # type: ignore[override]
            return 0.0

    engine = EvaluationEngine(
        llm_gateway=FakeLLMGateway(_make_analysis()),
        embedding_gateway=CapturingEmbeddingGateway(),
    )
    await engine.evaluate_sample(_make_sample(), _make_raw_post())
    assert len(captured) == 1, "embed_text should be called exactly once"


# ---------------------------------------------------------------------------
# evaluate_sample — not a job offer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evaluate_sample_not_job_offer_all_fields_incorrect() -> None:
    analysis = _make_analysis(is_job_offer=False, summary="Not a mission post")
    engine = EvaluationEngine(
        llm_gateway=FakeLLMGateway(analysis),
        embedding_gateway=FakeEmbeddingGateway(),
    )
    result = await engine.evaluate_sample(_make_sample(), _make_raw_post())
    assert not result.company.correct
    assert not result.title.correct
    assert not result.contract.correct
    assert not result.remote.correct
    assert not result.stack.correct
    assert not result.tjm.correct
