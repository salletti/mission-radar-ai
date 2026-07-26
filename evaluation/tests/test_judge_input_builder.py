"""Tests for build_judge_input — pure string formatting, no I/O, no deepeval."""
from uuid import uuid4

from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode

from integrations.deepeval.judge_input_builder import build_judge_input


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
        seniority="senior",
        detected_tjm=650.0,
    )
    defaults.update(kwargs)
    return AnalyzedPost(**defaults)


def test_serializes_all_scalar_fields() -> None:
    post = _make_analyzed_post()
    text = build_judge_input(post)
    assert "Développeur Python Senior" in text
    assert "Accenture" in text
    assert "Paris, France" in text
    assert "senior" in text
    assert "650.0" in text
    assert "Mission freelance Python Senior" in text


def test_none_optional_fields_render_as_unknown() -> None:
    post = _make_analyzed_post(title=None, company=None, location=None, seniority=None, detected_tjm=None)
    text = build_judge_input(post)
    assert "Title: unknown" in text
    assert "Company: unknown" in text
    assert "Location: unknown" in text
    assert "Seniority: unknown" in text
    assert "Daily rate (TJM): unknown" in text
    assert "None" not in text


def test_empty_stack_renders_as_none() -> None:
    post = _make_analyzed_post(detected_stack=())
    text = build_judge_input(post)
    assert "Technology stack: none" in text


def test_stack_is_comma_joined() -> None:
    post = _make_analyzed_post(detected_stack=("python", "docker"))
    text = build_judge_input(post)
    assert "Technology stack: python, docker" in text


def test_enum_values_use_dot_value_not_repr() -> None:
    post = _make_analyzed_post(
        detected_contract_type=ContractType.FREELANCE,
        detected_remote_mode=RemoteMode.HYBRID,
    )
    text = build_judge_input(post)
    assert "Contract type: freelance" in text
    assert "Remote mode: hybrid" in text
    assert "ContractType." not in text
    assert "RemoteMode." not in text


def test_summary_always_included_verbatim() -> None:
    post = _make_analyzed_post(summary="A very specific summary sentence.")
    text = build_judge_input(post)
    assert "Summary: A very specific summary sentence." in text
