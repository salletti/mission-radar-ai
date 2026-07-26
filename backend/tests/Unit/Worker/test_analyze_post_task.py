"""Unit tests for analyze_post_task — no DB, no network, no Celery broker."""
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.Domain.ValueObject.post_analysis import PostAnalysis
from src.Infrastructure.External.LLM.exceptions import LLMExtractionError
from src.Infrastructure.Worker.tasks.analyze_post_task import _analyze


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeRawPost:
    def __init__(self) -> None:
        self.id = uuid4()


class FakeAnalyzedPostRepository:
    def __init__(self) -> None:
        self._store: dict[UUID, object] = {}
        self._by_raw: dict[UUID, object] = {}

    async def save(self, analyzed_post: object) -> None:
        self._store[analyzed_post.id] = analyzed_post  # type: ignore[attr-defined]
        self._by_raw[analyzed_post.raw_post_id] = analyzed_post  # type: ignore[attr-defined]

    async def get_by_raw_post_id(self, raw_post_id: UUID) -> Optional[object]:
        return self._by_raw.get(raw_post_id)

    async def get_by_id(self, post_id: UUID) -> Optional[object]:
        return self._store.get(post_id)

    async def list_today_missions(self) -> list:
        return []

    async def list_missions(self, limit: int) -> list:
        return []


class FakeLLMGateway:
    def __init__(self, analysis: PostAnalysis) -> None:
        self._analysis = analysis

    async def analyze_post(self, raw_post: object) -> PostAnalysis:
        return self._analysis

    async def extract_profile_from_cv(self, cv_text: str) -> object: ...
    async def summarize_mission(self, content: str) -> str: ...
    async def generate_search_queries(self, profile: object) -> list: ...


class FakeLLMGatewayRaising:
    async def analyze_post(self, raw_post: object) -> PostAnalysis:
        raise LLMExtractionError("Groq timeout")

    async def extract_profile_from_cv(self, cv_text: str) -> object: ...
    async def summarize_mission(self, content: str) -> str: ...
    async def generate_search_queries(self, profile: object) -> list: ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_ctx() -> tuple[MagicMock, MagicMock]:
    """Renvoie (mock_AsyncSessionLocal, mock_session) — prêt pour `async with`."""
    session = MagicMock()
    session.commit = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return MagicMock(return_value=ctx), session


def _make_raw_post_repo(raw_post: Optional[object]) -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=raw_post)
    return repo


def _job_offer_analysis() -> PostAnalysis:
    return PostAnalysis(
        summary="Mission Python freelance senior.",
        required_skills=("python", "fastapi"),
        nice_to_have_skills=(),
        is_job_offer=True,
        contract_type="freelance",
        remote_policy="full remote",
        daily_rate="700€/j",
    )


def _non_offer_analysis() -> PostAnalysis:
    return PostAnalysis(
        summary="Article de blog sur Python.",
        required_skills=(),
        nice_to_have_skills=(),
        is_job_offer=False,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_raw_post_not_found_raises_value_error() -> None:
    """RawPost introuvable → ValueError, pas de retry."""
    mock_session_local, _ = _make_session_ctx()
    fake_raw_repo = _make_raw_post_repo(None)
    fake_analyzed_repo = FakeAnalyzedPostRepository()

    with patch("src.Infrastructure.Worker.tasks.analyze_post_task.AsyncSessionLocal", mock_session_local), \
         patch("src.Infrastructure.Worker.tasks.analyze_post_task.SqlAlchemyRawPostRepository", return_value=fake_raw_repo), \
         patch("src.Infrastructure.Worker.tasks.analyze_post_task.SqlAlchemyAnalyzedPostRepository", return_value=fake_analyzed_repo):
        with pytest.raises(ValueError, match="not found"):
            await _analyze(str(uuid4()))


@pytest.mark.asyncio
async def test_already_analyzed_returns_correct_status() -> None:
    """Post déjà analysé → status='already_analyzed', pas de nouvel appel LLM."""
    raw_post = FakeRawPost()
    fake_raw_repo = _make_raw_post_repo(raw_post)

    existing_analyzed_id = uuid4()

    class FakeAnalyzedRepoWithExisting(FakeAnalyzedPostRepository):
        async def get_by_raw_post_id(self, raw_post_id: UUID) -> Optional[object]:
            existing = MagicMock()
            existing.id = existing_analyzed_id
            return existing

    fake_analyzed_repo = FakeAnalyzedRepoWithExisting()
    mock_session_local, _ = _make_session_ctx()
    fake_llm = FakeLLMGateway(_job_offer_analysis())

    with patch("src.Infrastructure.Worker.tasks.analyze_post_task.AsyncSessionLocal", mock_session_local), \
         patch("src.Infrastructure.Worker.tasks.analyze_post_task.SqlAlchemyRawPostRepository", return_value=fake_raw_repo), \
         patch("src.Infrastructure.Worker.tasks.analyze_post_task.SqlAlchemyAnalyzedPostRepository", return_value=fake_analyzed_repo), \
         patch("src.Infrastructure.Worker.tasks.analyze_post_task.GroqLLMGateway", return_value=fake_llm):
        result = await _analyze(str(raw_post.id))

    assert result["status"] == "already_analyzed"
    assert result["analyzed_post_id"] == str(existing_analyzed_id)


@pytest.mark.asyncio
async def test_not_job_offer_returns_skipped() -> None:
    """Post non-offre → status='skipped', rien persisté."""
    raw_post = FakeRawPost()
    fake_raw_repo = _make_raw_post_repo(raw_post)
    fake_analyzed_repo = FakeAnalyzedPostRepository()
    fake_llm = FakeLLMGateway(_non_offer_analysis())
    mock_session_local, _ = _make_session_ctx()

    with patch("src.Infrastructure.Worker.tasks.analyze_post_task.AsyncSessionLocal", mock_session_local), \
         patch("src.Infrastructure.Worker.tasks.analyze_post_task.SqlAlchemyRawPostRepository", return_value=fake_raw_repo), \
         patch("src.Infrastructure.Worker.tasks.analyze_post_task.SqlAlchemyAnalyzedPostRepository", return_value=fake_analyzed_repo), \
         patch("src.Infrastructure.Worker.tasks.analyze_post_task.GroqLLMGateway", return_value=fake_llm):
        result = await _analyze(str(raw_post.id))

    assert result["status"] == "skipped"
    assert result["analyzed_post_id"] is None


@pytest.mark.asyncio
async def test_analyzed_successfully_returns_analyzed_post_id() -> None:
    """Post offre valide → status='analyzed', analyzed_post_id présent."""

    raw_post = FakeRawPost()
    fake_raw_repo = _make_raw_post_repo(raw_post)
    fake_analyzed_repo = FakeAnalyzedPostRepository()
    fake_llm = FakeLLMGateway(_job_offer_analysis())
    mock_session_local, _ = _make_session_ctx()

    with patch("src.Infrastructure.Worker.tasks.analyze_post_task.AsyncSessionLocal", mock_session_local), \
         patch("src.Infrastructure.Worker.tasks.analyze_post_task.SqlAlchemyRawPostRepository", return_value=fake_raw_repo), \
         patch("src.Infrastructure.Worker.tasks.analyze_post_task.SqlAlchemyAnalyzedPostRepository", return_value=fake_analyzed_repo), \
         patch("src.Infrastructure.Worker.tasks.analyze_post_task.GroqLLMGateway", return_value=fake_llm):
        result = await _analyze(str(raw_post.id))

    assert result["status"] == "analyzed"
    assert result["analyzed_post_id"] is not None
    # Valide que c'est un UUID valide
    UUID(result["analyzed_post_id"])


@pytest.mark.asyncio
async def test_llm_extraction_error_is_propagated() -> None:
    """LLMExtractionError propagée depuis _analyze — le wrapper sync gère le retry."""
    raw_post = FakeRawPost()
    fake_raw_repo = _make_raw_post_repo(raw_post)
    fake_analyzed_repo = FakeAnalyzedPostRepository()
    fake_llm = FakeLLMGatewayRaising()
    mock_session_local, _ = _make_session_ctx()

    with patch("src.Infrastructure.Worker.tasks.analyze_post_task.AsyncSessionLocal", mock_session_local), \
         patch("src.Infrastructure.Worker.tasks.analyze_post_task.SqlAlchemyRawPostRepository", return_value=fake_raw_repo), \
         patch("src.Infrastructure.Worker.tasks.analyze_post_task.SqlAlchemyAnalyzedPostRepository", return_value=fake_analyzed_repo), \
         patch("src.Infrastructure.Worker.tasks.analyze_post_task.GroqLLMGateway", return_value=fake_llm):
        with pytest.raises(LLMExtractionError):
            await _analyze(str(raw_post.id))
