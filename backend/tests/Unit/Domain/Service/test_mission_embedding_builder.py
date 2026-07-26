"""Unit tests for MissionEmbeddingBuilder — pure domain service, no I/O."""
from uuid import uuid4

import pytest

from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Service.mission_embedding_builder import MissionEmbeddingBuilder
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode


def _make_post(**kwargs) -> AnalyzedPost:
    defaults = {
        "raw_post_id": uuid4(),
        "summary": "Mission Python senior, FastAPI, architecture hexagonale.",
        "detected_stack": ("fastapi", "postgresql", "python"),
        "detected_contract_type": ContractType.FREELANCE,
        "detected_remote_mode": RemoteMode.FULL_REMOTE,
        "title": "Lead Python Developer",
        "company": "Acme Corp",
        "location": "Paris",
    }
    return AnalyzedPost(**{**defaults, **kwargs})


@pytest.fixture
def builder() -> MissionEmbeddingBuilder:
    return MissionEmbeddingBuilder()


def test_complete_mission(builder: MissionEmbeddingBuilder) -> None:
    post = _make_post()
    result = builder.build_matching_text(post)

    assert "Lead Python Developer" in result
    assert "Acme Corp" in result
    assert "Mission Python senior" in result
    assert "fastapi postgresql python" in result
    assert "freelance" in result
    assert "full_remote" in result
    assert "Paris" in result


def test_without_location(builder: MissionEmbeddingBuilder) -> None:
    post = _make_post(location=None)
    result = builder.build_matching_text(post)

    assert "Paris" not in result
    assert "Mission Python senior" in result
    assert "freelance" in result


def test_without_stack(builder: MissionEmbeddingBuilder) -> None:
    post = _make_post(detected_stack=())
    result = builder.build_matching_text(post)

    assert "fastapi" not in result
    assert "Mission Python senior" in result
    assert "freelance" in result
    assert "full_remote" in result


def test_no_optional_fields(builder: MissionEmbeddingBuilder) -> None:
    post = _make_post(
        title=None,
        company=None,
        location=None,
        detected_stack=(),
    )
    result = builder.build_matching_text(post)
    lines = result.splitlines()

    assert lines[0] == "Mission Python senior, FastAPI, architecture hexagonale."
    assert "freelance" in result
    assert "full_remote" in result
    assert len(lines) == 3
