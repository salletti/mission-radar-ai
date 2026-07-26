"""Integration tests for _analyze() — real PostgreSQL + mocked LLM + mocked embedding."""
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest

from src.Application.Gateway.embedding_gateway import EmbeddingGateway
from src.Domain.Entity.raw_post import RawPost
from src.Domain.ValueObject.post_analysis import PostAnalysis
from src.Infrastructure.Config.database import AsyncSessionLocal
from src.Infrastructure.Persistence.Repository.analyzed_post_repository import SqlAlchemyAnalyzedPostRepository
from src.Infrastructure.Persistence.Repository.raw_post_repository import SqlAlchemyRawPostRepository
from src.Infrastructure.Worker.tasks.analyze_post_task import _analyze

_NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeEmbeddingGateway(EmbeddingGateway):
    async def embed_text(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    async def compute_similarity(self, a: list[float], b: list[float]) -> float:
        return 1.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_raw_post() -> RawPost:
    uid = uuid4()
    return RawPost(
        id=uuid4(),
        source="linkedin",
        external_id=str(uid),
        author_name="Recruteur Test",
        author_url="https://linkedin.com/in/test",
        content="Mission Python freelance senior full remote TJM 700€/j #freelance #python",
        post_url=f"https://linkedin.com/posts/{uid}",
        published_at=_NOW,
        scraped_at=_NOW,
    )


def _job_offer_analysis() -> PostAnalysis:
    return PostAnalysis(
        summary="Mission Python freelance senior full remote 700€/j.",
        required_skills=("python", "fastapi"),
        nice_to_have_skills=("docker",),
        is_job_offer=True,
        title="Senior Python Engineer",
        contract_type="freelance",
        remote_policy="full remote",
        daily_rate="700€/j",
    )


def _non_offer_analysis() -> PostAnalysis:
    return PostAnalysis(
        summary="Article de blog Python.",
        required_skills=(),
        nice_to_have_skills=(),
        is_job_offer=False,
    )


async def _insert_raw_post(raw_post: RawPost) -> None:
    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyRawPostRepository(session)
        await repo.save(raw_post)
        await session.commit()


async def _count_analyzed_posts() -> int:
    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyAnalyzedPostRepository(session)
        posts = await repo.list_missions(limit=1000)
        return len(posts)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_persists_analyzed_post() -> None:
    """Post offre valide → AnalyzedPost persisté en base."""
    raw_post = _make_raw_post()
    await _insert_raw_post(raw_post)

    fake_llm = _job_offer_analysis()

    with patch(
        "src.Infrastructure.Worker.tasks.analyze_post_task.GroqLLMGateway"
    ) as MockLLM, patch(
        "src.Infrastructure.Worker.tasks.analyze_post_task._get_embedding_gateway",
        return_value=FakeEmbeddingGateway(),
    ):
        instance = MockLLM.return_value
        instance.analyze_post = lambda _: _async_return(fake_llm)
        result = await _analyze(str(raw_post.id))

    assert result["status"] == "analyzed"
    assert result["analyzed_post_id"] is not None
    assert await _count_analyzed_posts() == 1


@pytest.mark.asyncio
async def test_analyze_idempotent_already_analyzed() -> None:
    """Deuxième appel sur même post → status='already_analyzed', pas de doublon."""
    raw_post = _make_raw_post()
    await _insert_raw_post(raw_post)

    fake_llm = _job_offer_analysis()

    with patch(
        "src.Infrastructure.Worker.tasks.analyze_post_task.GroqLLMGateway"
    ) as MockLLM, patch(
        "src.Infrastructure.Worker.tasks.analyze_post_task._get_embedding_gateway",
        return_value=FakeEmbeddingGateway(),
    ):
        instance = MockLLM.return_value
        instance.analyze_post = lambda _: _async_return(fake_llm)
        first = await _analyze(str(raw_post.id))

    with patch(
        "src.Infrastructure.Worker.tasks.analyze_post_task.GroqLLMGateway"
    ) as MockLLM, patch(
        "src.Infrastructure.Worker.tasks.analyze_post_task._get_embedding_gateway",
        return_value=FakeEmbeddingGateway(),
    ):
        instance = MockLLM.return_value
        instance.analyze_post = lambda _: _async_return(fake_llm)
        second = await _analyze(str(raw_post.id))

    assert first["status"] == "analyzed"
    assert second["status"] == "already_analyzed"
    assert second["analyzed_post_id"] == first["analyzed_post_id"]
    assert await _count_analyzed_posts() == 1


@pytest.mark.asyncio
async def test_analyze_non_offer_skipped_no_persistence() -> None:
    """Post non-offre → status='skipped', aucun AnalyzedPost en base."""
    raw_post = _make_raw_post()
    await _insert_raw_post(raw_post)

    fake_llm = _non_offer_analysis()

    with patch(
        "src.Infrastructure.Worker.tasks.analyze_post_task.GroqLLMGateway"
    ) as MockLLM, patch(
        "src.Infrastructure.Worker.tasks.analyze_post_task._get_embedding_gateway",
        return_value=FakeEmbeddingGateway(),
    ):
        instance = MockLLM.return_value
        instance.analyze_post = lambda _: _async_return(fake_llm)
        result = await _analyze(str(raw_post.id))

    assert result["status"] == "skipped"
    assert result["analyzed_post_id"] is None
    assert await _count_analyzed_posts() == 0


@pytest.mark.asyncio
async def test_analyze_raw_post_not_found_raises() -> None:
    """RawPost inexistant → ValueError."""
    with pytest.raises(ValueError, match="not found"):
        await _analyze(str(uuid4()))


@pytest.mark.asyncio
async def test_analyze_persists_embedding() -> None:
    """Post offre valide → AnalyzedPost.embedding non-None et non-vide."""
    raw_post = _make_raw_post()
    await _insert_raw_post(raw_post)

    fake_llm = _job_offer_analysis()

    with patch(
        "src.Infrastructure.Worker.tasks.analyze_post_task.GroqLLMGateway"
    ) as MockLLM, patch(
        "src.Infrastructure.Worker.tasks.analyze_post_task._get_embedding_gateway",
        return_value=FakeEmbeddingGateway(),
    ):
        instance = MockLLM.return_value
        instance.analyze_post = lambda _: _async_return(fake_llm)
        result = await _analyze(str(raw_post.id))

    assert result["status"] == "analyzed"

    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyAnalyzedPostRepository(session)
        saved = await repo.get_by_id(UUID(result["analyzed_post_id"]))
        assert saved is not None
        assert saved.embedding is not None
        assert len(saved.embedding) > 0


# ---------------------------------------------------------------------------
# Async helper (évite la syntaxe async lambda)
# ---------------------------------------------------------------------------

async def _async_return(value):
    return value
