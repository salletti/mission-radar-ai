"""Unit tests for AnalyzeRawPost use case — no I/O, no DB, no external services."""
import pytest
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from src.Application.Gateway.embedding_gateway import EmbeddingGateway
from src.Application.Gateway.llm_gateway import LLMGateway
from src.Application.UseCase.analyze_raw_post import AnalyzeRawPost
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.raw_post import RawPost
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Service.mission_embedding_builder import MissionEmbeddingBuilder
from src.Domain.Service.mission_normalizer import MissionNormalizer
from src.Domain.ValueObject.post_analysis import PostAnalysis

_NOW = datetime(2026, 6, 20, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fake implementations
# ---------------------------------------------------------------------------


class FakeLLMGateway(LLMGateway):
    """Minimal LLM fake — only analyze_post() is implemented."""

    def __init__(self, result: PostAnalysis) -> None:
        self._result = result
        self.calls: list[RawPost] = []

    async def extract_profile_from_cv(self, cv_text: str):  # type: ignore[override]
        raise NotImplementedError

    async def summarize_mission(self, content: str) -> str:  # type: ignore[override]
        raise NotImplementedError

    async def generate_search_queries(self, profile) -> list[dict]:  # type: ignore[override]
        raise NotImplementedError

    async def analyze_post(self, raw_post: RawPost) -> PostAnalysis:
        self.calls.append(raw_post)
        return self._result


class FakeAnalyzedPostRepository(AnalyzedPostRepository):
    def __init__(self, existing: AnalyzedPost | None = None) -> None:
        self._store: dict[UUID, AnalyzedPost] = {}
        self.save_calls: list[AnalyzedPost] = []
        if existing:
            self._store[existing.raw_post_id] = existing

    async def save(self, analyzed_post: AnalyzedPost) -> None:
        self._store[analyzed_post.raw_post_id] = analyzed_post
        self.save_calls.append(analyzed_post)

    async def get_by_id(self, post_id: UUID) -> Optional[AnalyzedPost]:
        for post in self._store.values():
            if post.id == post_id:
                return post
        return None

    async def get_by_raw_post_id(self, raw_post_id: UUID) -> Optional[AnalyzedPost]:
        return self._store.get(raw_post_id)

    async def list_today_missions(self) -> list[AnalyzedPost]:
        return list(self._store.values())

    async def list_missions(self, limit: int) -> list[AnalyzedPost]:
        return list(self._store.values())[:limit]

    async def find_by_raw_post_ids(self, raw_post_ids: list[UUID]) -> list[AnalyzedPost]:
        return [p for p in self._store.values() if p.raw_post_id in raw_post_ids]

    async def find_by_ids(self, ids: list[UUID]) -> list[AnalyzedPost]:
        return [p for p in self._store.values() if p.id in ids]


class FakeEmbeddingGateway(EmbeddingGateway):
    def __init__(self) -> None:
        self.embed_calls: list[str] = []

    async def embed_text(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return [0.1, 0.2, 0.3]

    async def compute_similarity(self, a: list[float], b: list[float]) -> float:
        return 1.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_raw_post() -> RawPost:
    return RawPost(
        source="linkedin",
        external_id="post-001",
        author_name="Alice Recruiter",
        author_url="https://linkedin.com/in/alice",
        content="Recherche développeur Python senior freelance full remote. TJM 700€.",
        post_url="https://linkedin.com/posts/post-001",
        published_at=_NOW,
        scraped_at=_NOW,
    )


def _make_post_analysis(is_job_offer: bool = True) -> PostAnalysis:
    return PostAnalysis(
        summary="Mission Python senior — full remote, TJM 700€.",
        required_skills=("python", "fastapi"),
        nice_to_have_skills=("docker",),
        is_job_offer=is_job_offer,
        contract_type="freelance",
        remote_policy="full_remote",
        daily_rate="700€",
    )


def _make_use_case(
    post_analysis: PostAnalysis | None = None,
    existing_post: AnalyzedPost | None = None,
) -> tuple[AnalyzeRawPost, FakeLLMGateway, FakeAnalyzedPostRepository, FakeEmbeddingGateway]:
    analysis = post_analysis or _make_post_analysis()
    fake_llm = FakeLLMGateway(result=analysis)
    repo = FakeAnalyzedPostRepository(existing=existing_post)
    fake_embedding = FakeEmbeddingGateway()
    uc = AnalyzeRawPost(
        llm=fake_llm,
        mission_normalizer=MissionNormalizer(),
        mission_embedding_builder=MissionEmbeddingBuilder(),
        embedding_gateway=fake_embedding,
        analyzed_post_repository=repo,
    )
    return uc, fake_llm, repo, fake_embedding


# ---------------------------------------------------------------------------
# Tests — existing behaviour (unchanged)
# ---------------------------------------------------------------------------


async def test_already_analyzed_returns_correct_status() -> None:
    raw_post = _make_raw_post()
    existing = AnalyzedPost(raw_post_id=raw_post.id, summary="Already analyzed.")
    uc, _, _, _ = _make_use_case(existing_post=existing)

    result = await uc.execute(raw_post)

    assert result.status == "already_analyzed"
    assert result.analyzed_post_id == existing.id


async def test_already_analyzed_does_not_call_llm() -> None:
    raw_post = _make_raw_post()
    existing = AnalyzedPost(raw_post_id=raw_post.id, summary="Already analyzed.")
    uc, fake_llm, _, _ = _make_use_case(existing_post=existing)

    await uc.execute(raw_post)

    assert fake_llm.calls == []


async def test_not_job_offer_returns_skipped_status() -> None:
    raw_post = _make_raw_post()
    uc, _, _, _ = _make_use_case(post_analysis=_make_post_analysis(is_job_offer=False))

    result = await uc.execute(raw_post)

    assert result.status == "skipped"
    assert result.reason == "not_job_offer"


async def test_not_job_offer_does_not_save() -> None:
    raw_post = _make_raw_post()
    uc, _, repo, _ = _make_use_case(post_analysis=_make_post_analysis(is_job_offer=False))

    await uc.execute(raw_post)

    assert repo.save_calls == []


async def test_valid_offer_returns_analyzed_status() -> None:
    raw_post = _make_raw_post()
    uc, _, _, _ = _make_use_case()

    result = await uc.execute(raw_post)

    assert result.status == "analyzed"
    assert result.analyzed_post_id is not None


async def test_valid_offer_analyzed_post_id_matches_persisted_entity() -> None:
    raw_post = _make_raw_post()
    uc, _, repo, _ = _make_use_case()

    result = await uc.execute(raw_post)

    assert len(repo.save_calls) == 1
    assert result.analyzed_post_id == repo.save_calls[0].id


async def test_llm_called_with_correct_raw_post() -> None:
    raw_post = _make_raw_post()
    uc, fake_llm, _, _ = _make_use_case()

    await uc.execute(raw_post)

    assert fake_llm.calls == [raw_post]


async def test_mission_normalizer_called_with_correct_raw_post_id() -> None:
    raw_post = _make_raw_post()
    uc, _, repo, _ = _make_use_case()

    await uc.execute(raw_post)

    assert len(repo.save_calls) == 1
    assert repo.save_calls[0].raw_post_id == raw_post.id


async def test_mission_normalizer_merges_skills_into_detected_stack() -> None:
    raw_post = _make_raw_post()
    uc, _, repo, _ = _make_use_case()

    await uc.execute(raw_post)

    # MissionNormalizer merges required + nice_to_have, lowercased, sorted
    assert repo.save_calls[0].detected_stack == ("docker", "fastapi", "python")


async def test_save_called_exactly_once_for_valid_offer() -> None:
    raw_post = _make_raw_post()
    uc, _, repo, _ = _make_use_case()

    await uc.execute(raw_post)

    assert len(repo.save_calls) == 1


# ---------------------------------------------------------------------------
# Tests — Phase 5.0.3 : embedding generation
# ---------------------------------------------------------------------------


async def test_valid_offer_sets_embedding_on_saved_post() -> None:
    raw_post = _make_raw_post()
    uc, _, repo, _ = _make_use_case()

    await uc.execute(raw_post)

    assert repo.save_calls[0].embedding == [0.1, 0.2, 0.3]


async def test_embedding_text_passed_to_gateway() -> None:
    raw_post = _make_raw_post()
    uc, _, repo, fake_embedding = _make_use_case()

    await uc.execute(raw_post)

    expected = MissionEmbeddingBuilder().build_matching_text(repo.save_calls[0])
    assert fake_embedding.embed_calls == [expected]


async def test_embedding_failure_raises_and_does_not_save() -> None:
    class FailingEmbeddingGateway(EmbeddingGateway):
        async def embed_text(self, text: str) -> list[float]:
            raise RuntimeError("embedding failed")

        async def compute_similarity(self, a: list[float], b: list[float]) -> float:
            return 0.0

    raw_post = _make_raw_post()
    analysis = _make_post_analysis()
    repo = FakeAnalyzedPostRepository()
    uc = AnalyzeRawPost(
        llm=FakeLLMGateway(result=analysis),
        mission_normalizer=MissionNormalizer(),
        mission_embedding_builder=MissionEmbeddingBuilder(),
        embedding_gateway=FailingEmbeddingGateway(),
        analyzed_post_repository=repo,
    )

    with pytest.raises(RuntimeError, match="embedding failed"):
        await uc.execute(raw_post)

    assert repo.save_calls == []


async def test_not_job_offer_does_not_call_embedding_gateway() -> None:
    raw_post = _make_raw_post()
    uc, _, _, fake_embedding = _make_use_case(post_analysis=_make_post_analysis(is_job_offer=False))

    await uc.execute(raw_post)

    assert fake_embedding.embed_calls == []
