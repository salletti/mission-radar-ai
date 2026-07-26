"""Tests for ExtractionEvaluator — no LLM, no pipeline, pure comparison logic."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from evaluators.extraction_evaluator import ExtractionEvaluator
from models.gold_sample import GoldSample


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sample(**kwargs) -> GoldSample:
    defaults = dict(
        raw_post_id="urn:li:activity:1111111111111111111",
        post_content="Mission Python Senior freelance Paris hybrid 650€/j",
        expected_company="Accenture",
        expected_title="Développeur Python Senior",
        expected_location="Paris, France",
        expected_contract="freelance",
        expected_remote="hybrid",
        expected_stack=["python", "fastapi", "postgresql"],
        expected_tjm=650.0,
        expected_salary=None,
    )
    defaults.update(kwargs)
    return GoldSample(**defaults)


def _make_analyzed_post(**kwargs) -> AnalyzedPost:
    defaults = dict(
        raw_post_id=uuid4(),
        summary="Mission freelance Python Senior",
        detected_stack=("fastapi", "postgresql", "python"),
        detected_contract_type=ContractType.FREELANCE,
        detected_remote_mode=RemoteMode.HYBRID,
        title="Développeur Python Senior",
        company="Accenture",
        location="Paris, France",
        detected_tjm=650.0,
    )
    defaults.update(kwargs)
    return AnalyzedPost(**defaults)


_EVALUATOR = ExtractionEvaluator()


# ---------------------------------------------------------------------------
# Perfect extraction
# ---------------------------------------------------------------------------


def test_perfect_extraction_all_correct() -> None:
    sample = _make_sample()
    post = _make_analyzed_post()
    result = _EVALUATOR.evaluate(sample, post)
    assert result.company.correct
    assert result.title.correct
    assert result.contract.correct
    assert result.location.correct
    assert result.remote.correct
    assert result.stack.correct
    assert result.stack.missing == []
    assert result.stack.unexpected == []
    assert result.tjm.correct


def test_sample_id_equals_raw_post_id() -> None:
    sample = _make_sample(raw_post_id="urn:li:activity:9999")
    result = _EVALUATOR.evaluate(sample, _make_analyzed_post())
    assert result.sample_id == "urn:li:activity:9999"


# ---------------------------------------------------------------------------
# Individual field failures
# ---------------------------------------------------------------------------


def test_wrong_company() -> None:
    sample = _make_sample(expected_company="Accenture")
    post = _make_analyzed_post(company="Capgemini")
    result = _EVALUATOR.evaluate(sample, post)
    assert not result.company.correct
    assert result.company.expected == "Accenture"
    assert result.company.actual == "Capgemini"


def test_wrong_title() -> None:
    sample = _make_sample(expected_title="Tech Lead")
    post = _make_analyzed_post(title="Junior Developer")
    result = _EVALUATOR.evaluate(sample, post)
    assert not result.title.correct


def test_wrong_contract() -> None:
    sample = _make_sample(expected_contract="freelance")
    post = _make_analyzed_post(detected_contract_type=ContractType.PERMANENT)
    result = _EVALUATOR.evaluate(sample, post)
    assert not result.contract.correct
    assert result.contract.expected == "freelance"
    assert result.contract.actual == "permanent"


def test_wrong_remote() -> None:
    sample = _make_sample(expected_remote="full_remote")
    post = _make_analyzed_post(detected_remote_mode=RemoteMode.ONSITE)
    result = _EVALUATOR.evaluate(sample, post)
    assert not result.remote.correct


def test_wrong_location() -> None:
    sample = _make_sample(expected_location="Paris, France")
    post = _make_analyzed_post(location="Lyon, France")
    result = _EVALUATOR.evaluate(sample, post)
    assert not result.location.correct


def test_wrong_tjm() -> None:
    sample = _make_sample(expected_tjm=650.0)
    post = _make_analyzed_post(detected_tjm=500.0)
    result = _EVALUATOR.evaluate(sample, post)
    assert not result.tjm.correct


# ---------------------------------------------------------------------------
# String comparison — case insensitive
# ---------------------------------------------------------------------------


def test_company_comparison_is_case_insensitive() -> None:
    sample = _make_sample(expected_company="accenture")
    post = _make_analyzed_post(company="ACCENTURE")
    result = _EVALUATOR.evaluate(sample, post)
    assert result.company.correct


def test_location_comparison_strips_whitespace() -> None:
    sample = _make_sample(expected_location="  Paris, France  ")
    post = _make_analyzed_post(location="Paris, France")
    result = _EVALUATOR.evaluate(sample, post)
    assert result.location.correct


# ---------------------------------------------------------------------------
# Stack variations
# ---------------------------------------------------------------------------


def test_stack_identical() -> None:
    sample = _make_sample(expected_stack=["python", "fastapi"])
    post = _make_analyzed_post(detected_stack=("fastapi", "python"))
    result = _EVALUATOR.evaluate(sample, post)
    assert result.stack.correct
    assert result.stack.missing == []
    assert result.stack.unexpected == []


def test_stack_with_missing_elements() -> None:
    sample = _make_sample(expected_stack=["python", "fastapi", "docker"])
    post = _make_analyzed_post(detected_stack=("python", "fastapi"))
    result = _EVALUATOR.evaluate(sample, post)
    assert not result.stack.correct
    assert "docker" in result.stack.missing
    assert result.stack.unexpected == []


def test_stack_with_unexpected_elements() -> None:
    sample = _make_sample(expected_stack=["python"])
    post = _make_analyzed_post(detected_stack=("python", "kubernetes", "terraform"))
    result = _EVALUATOR.evaluate(sample, post)
    assert not result.stack.correct
    assert result.stack.missing == []
    assert "kubernetes" in result.stack.unexpected
    assert "terraform" in result.stack.unexpected


def test_stack_with_both_missing_and_unexpected() -> None:
    sample = _make_sample(expected_stack=["python", "fastapi"])
    post = _make_analyzed_post(detected_stack=("python", "django"))
    result = _EVALUATOR.evaluate(sample, post)
    assert not result.stack.correct
    assert "fastapi" in result.stack.missing
    assert "django" in result.stack.unexpected


# ---------------------------------------------------------------------------
# Null values
# ---------------------------------------------------------------------------


def test_both_company_none_is_correct() -> None:
    sample = _make_sample(expected_company=None)
    post = _make_analyzed_post(company=None)
    result = _EVALUATOR.evaluate(sample, post)
    assert result.company.correct


def test_expected_company_none_actual_present_is_incorrect() -> None:
    sample = _make_sample(expected_company=None)
    post = _make_analyzed_post(company="Accenture")
    result = _EVALUATOR.evaluate(sample, post)
    assert not result.company.correct


def test_expected_company_present_actual_none_is_incorrect() -> None:
    sample = _make_sample(expected_company="Accenture")
    post = _make_analyzed_post(company=None)
    result = _EVALUATOR.evaluate(sample, post)
    assert not result.company.correct


def test_both_tjm_none_is_correct() -> None:
    sample = _make_sample(expected_tjm=None)
    post = _make_analyzed_post(detected_tjm=None)
    result = _EVALUATOR.evaluate(sample, post)
    assert result.tjm.correct


def test_expected_tjm_none_actual_present_is_incorrect() -> None:
    sample = _make_sample(expected_tjm=None)
    post = _make_analyzed_post(detected_tjm=650.0)
    result = _EVALUATOR.evaluate(sample, post)
    assert not result.tjm.correct


def test_expected_tjm_present_actual_none_is_incorrect() -> None:
    sample = _make_sample(expected_tjm=650.0)
    post = _make_analyzed_post(detected_tjm=None)
    result = _EVALUATOR.evaluate(sample, post)
    assert not result.tjm.correct


def test_tjm_within_1_percent_tolerance_is_correct() -> None:
    sample = _make_sample(expected_tjm=650.0)
    post = _make_analyzed_post(detected_tjm=654.0)  # < 1% diff
    result = _EVALUATOR.evaluate(sample, post)
    assert result.tjm.correct


def test_tjm_beyond_1_percent_tolerance_is_incorrect() -> None:
    sample = _make_sample(expected_tjm=650.0)
    post = _make_analyzed_post(detected_tjm=700.0)  # > 1% diff
    result = _EVALUATOR.evaluate(sample, post)
    assert not result.tjm.correct


# ---------------------------------------------------------------------------
# AnalyzedPost is None (LLM classified post as not a job offer)
# ---------------------------------------------------------------------------


def test_none_analyzed_post_all_fields_incorrect() -> None:
    sample = _make_sample()
    result = _EVALUATOR.evaluate(sample, None)
    assert not result.company.correct
    assert not result.title.correct
    assert not result.contract.correct
    assert not result.location.correct
    assert not result.remote.correct
    assert not result.stack.correct
    assert not result.tjm.correct


def test_none_analyzed_post_stack_missing_equals_expected() -> None:
    sample = _make_sample(expected_stack=["python", "fastapi"])
    result = _EVALUATOR.evaluate(sample, None)
    assert set(result.stack.missing) == {"python", "fastapi"}
    assert result.stack.unexpected == []


def test_none_analyzed_post_contract_preserves_expected() -> None:
    sample = _make_sample(expected_contract="permanent")
    result = _EVALUATOR.evaluate(sample, None)
    assert result.contract.expected == "permanent"
    assert result.contract.actual is None
