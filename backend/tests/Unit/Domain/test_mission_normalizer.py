"""Unit tests for MissionNormalizer — pure domain service, no I/O."""
from uuid import uuid4

import pytest

from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Service.mission_normalizer import MissionNormalizer
from src.Domain.ValueObject.post_analysis import PostAnalysis
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode


def _make_result(**kwargs) -> PostAnalysis:
    defaults = {
        "summary": "Mission Python senior full remote",
        "required_skills": (),
        "nice_to_have_skills": (),
        "is_job_offer": True,
    }
    return PostAnalysis(**{**defaults, **kwargs})


@pytest.fixture
def normalizer() -> MissionNormalizer:
    return MissionNormalizer()


# ---------------------------------------------------------------------------
# normalize() — output type and base fields
# ---------------------------------------------------------------------------


def test_normalize_returns_analyzed_post(normalizer):
    result = normalizer.normalize(uuid4(), _make_result())
    assert isinstance(result, AnalyzedPost)


def test_normalize_copies_summary(normalizer):
    result = normalizer.normalize(uuid4(), _make_result(summary="Mission FastAPI backend."))
    assert result.summary == "Mission FastAPI backend."


def test_normalize_copies_optional_fields(normalizer):
    result = normalizer.normalize(
        uuid4(),
        _make_result(
            title="Lead Python",
            company="Acme",
            location="Paris",
            seniority="senior",
        ),
    )
    assert result.title == "Lead Python"
    assert result.company == "Acme"
    assert result.location == "Paris"
    assert result.seniority == "senior"


def test_normalize_sets_raw_post_id(normalizer):
    raw_post_id = uuid4()
    result = normalizer.normalize(raw_post_id, _make_result())
    assert result.raw_post_id == raw_post_id


# ---------------------------------------------------------------------------
# _merge_stack — fusion required + nice_to_have
# ---------------------------------------------------------------------------


def test_merge_stack_combines_both_lists(normalizer):
    result = normalizer.normalize(
        uuid4(),
        _make_result(
            required_skills=("Python", "FastAPI"),
            nice_to_have_skills=("Docker",),
        ),
    )
    assert "python" in result.detected_stack
    assert "fastapi" in result.detected_stack
    assert "docker" in result.detected_stack


def test_merge_stack_deduplicates(normalizer):
    result = normalizer.normalize(
        uuid4(),
        _make_result(
            required_skills=("Python", "python", "PYTHON"),
            nice_to_have_skills=("Python",),
        ),
    )
    assert result.detected_stack.count("python") == 1


def test_merge_stack_lowercases(normalizer):
    result = normalizer.normalize(
        uuid4(),
        _make_result(required_skills=("FastAPI", "DOCKER")),
    )
    assert "fastapi" in result.detected_stack
    assert "docker" in result.detected_stack
    assert "FastAPI" not in result.detected_stack


def test_merge_stack_sorted_alphabetically(normalizer):
    result = normalizer.normalize(
        uuid4(),
        _make_result(required_skills=("react", "python", "docker")),
    )
    assert result.detected_stack == ("docker", "python", "react")


def test_merge_stack_empty_returns_empty_tuple(normalizer):
    result = normalizer.normalize(
        uuid4(),
        _make_result(required_skills=(), nice_to_have_skills=()),
    )
    assert result.detected_stack == ()


# ---------------------------------------------------------------------------
# _parse_tjm — daily rate string → float
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "daily_rate, expected",
    [
        ("650€/j", 650.0),
        ("700 €/jour", 700.0),
        ("TJM 600€", 600.0),
        ("env. 650€", 650.0),
        ("650,00€", 650.0),
        ("750.0€", 750.0),
    ],
)
def test_parse_tjm_single_value(normalizer, daily_rate, expected):
    result = normalizer.normalize(
        uuid4(),
        _make_result(daily_rate=daily_rate),
    )
    assert result.detected_tjm == pytest.approx(expected)


def test_parse_tjm_range_returns_average(normalizer):
    result = normalizer.normalize(uuid4(), _make_result(daily_rate="600-700€"))
    assert result.detected_tjm == pytest.approx(650.0)


def test_parse_tjm_none_returns_none(normalizer):
    result = normalizer.normalize(uuid4(), _make_result(daily_rate=None))
    assert result.detected_tjm is None


def test_parse_tjm_empty_string_returns_none(normalizer):
    result = normalizer.normalize(uuid4(), _make_result(daily_rate=""))
    assert result.detected_tjm is None


# ---------------------------------------------------------------------------
# _normalize_contract_type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("freelance", ContractType.FREELANCE),
        ("Freelance", ContractType.FREELANCE),
        ("mission freelance", ContractType.FREELANCE),
        ("cdi", ContractType.PERMANENT),
        ("CDI", ContractType.PERMANENT),
        ("permanent", ContractType.PERMANENT),
        ("cdd", ContractType.FIXED_TERM),
        ("stage", ContractType.INTERNSHIP),
        ("alternance", ContractType.APPRENTICESHIP),
        (None, ContractType.UNKNOWN),
        ("", ContractType.UNKNOWN),
        ("inconnu", ContractType.UNKNOWN),
    ],
)
def test_normalize_contract_type(normalizer, raw, expected):
    result = normalizer.normalize(uuid4(), _make_result(contract_type=raw))
    assert result.detected_contract_type == expected


# ---------------------------------------------------------------------------
# _normalize_remote_mode
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("full remote", RemoteMode.FULL_REMOTE),
        ("full_remote", RemoteMode.FULL_REMOTE),
        ("100% remote", RemoteMode.FULL_REMOTE),
        ("100% télétravail", RemoteMode.FULL_REMOTE),
        ("télétravail total", RemoteMode.FULL_REMOTE),
        ("remote", RemoteMode.FULL_REMOTE),
        ("hybride", RemoteMode.HYBRID),
        ("hybrid", RemoteMode.HYBRID),
        ("télétravail partiel", RemoteMode.HYBRID),
        ("présentiel", RemoteMode.ONSITE),
        ("onsite", RemoteMode.ONSITE),
        ("sur site", RemoteMode.ONSITE),
        (None, RemoteMode.UNKNOWN),
        ("", RemoteMode.UNKNOWN),
        ("non précisé", RemoteMode.UNKNOWN),
    ],
)
def test_normalize_remote_mode(normalizer, raw, expected):
    result = normalizer.normalize(uuid4(), _make_result(remote_policy=raw))
    assert result.detected_remote_mode == expected
