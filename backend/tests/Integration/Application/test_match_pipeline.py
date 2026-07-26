"""Integration test — MatchMissions → Persistence → GetTodayMissions pipeline.

Uses real SQLAlchemy session + real repositories. No LLM, no Apify.
Embeddings are deterministic zero-vectors to keep the test fast.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.Application.DTO.get_today_missions_query import GetTodayMissionsQuery
from src.Application.UseCase.get_today_missions import GetTodayMissions
from src.Application.UseCase.match_missions import MatchMissions
from src.Domain.Entity.search_query import SearchQuery
from src.Domain.Entity.search_query_raw_post import SearchQueryRawPost
from src.Domain.Service.mission_match_scorer import MissionMatchScorer
from src.Domain.ValueObject.match_score import MatchScore
from src.Infrastructure.Config.database import AsyncSessionLocal
from src.Infrastructure.Persistence.Repository.analyzed_post_repository import (
    SqlAlchemyAnalyzedPostRepository,
)
from src.Infrastructure.Persistence.Repository.mission_match_repository import (
    SqlAlchemyMissionMatchRepository,
)
from src.Infrastructure.Persistence.Repository.raw_post_repository import (
    SqlAlchemyRawPostRepository,
)
from src.Infrastructure.Persistence.Repository.search_query_raw_post_repository import (
    SqlAlchemySearchQueryRawPostRepository,
)
from src.Infrastructure.Persistence.Repository.search_query_repository import (
    SqlAlchemySearchQueryRepository,
)
from src.Infrastructure.Persistence.Repository.user_profile_repository import (
    SqlAlchemyUserProfileRepository,
)
from tests.Integration.Repository.conftest import (
    make_analyzed_post,
    make_raw_post,
    make_user_profile,
)


class _FakeEmbeddingGateway:
    """Returns identical deterministic embeddings so semantic_score == 1.0."""

    async def embed_text(self, text: str) -> list[float]:
        return [1.0] * 384

    async def compute_similarity(self, a: list[float], b: list[float]) -> float:
        return 1.0


@pytest.fixture
async def db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.mark.asyncio
async def test_match_pipeline_end_to_end(db_session: AsyncSession) -> None:
    """
    Full pipeline:
      1. Persist UserProfile + RawPost + AnalyzedPost + SearchQuery + link
      2. MatchMissions.execute() → writes MissionMatch to DB
      3. GetTodayMissions.execute() → reads MissionMatch + enriches → TodayMission DTOs
    """
    profile = make_user_profile(embedding=[1.0] * 384)
    raw = make_raw_post()
    analyzed = make_analyzed_post(raw_post_id=raw.id, embedding=[1.0] * 384)

    profile_repo = SqlAlchemyUserProfileRepository(db_session)
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    analyzed_repo = SqlAlchemyAnalyzedPostRepository(db_session)
    search_query_repo = SqlAlchemySearchQueryRepository(db_session)
    link_repo = SqlAlchemySearchQueryRawPostRepository(db_session)
    match_repo = SqlAlchemyMissionMatchRepository(db_session)

    await profile_repo.save(profile)
    await raw_repo.save(raw)
    await analyzed_repo.save(analyzed)

    search_query = SearchQuery(
        user_profile_id=profile.id,
        query="python freelance",
        source="linkedin",
        limit=50,
    )
    await search_query_repo.save_many([search_query])

    link = SearchQueryRawPost(search_query_id=search_query.id, raw_post_id=raw.id)
    await link_repo.save(link)

    # --- Step 2: MatchMissions persists MissionMatch ---
    gateway = _FakeEmbeddingGateway()
    scorer = MissionMatchScorer(gateway)
    match_uc = MatchMissions(
        scorer=scorer,
        search_query_repository=search_query_repo,
        search_query_raw_post_repository=link_repo,
        analyzed_post_repository=analyzed_repo,
        mission_match_repository=match_repo,
        min_score=0.0,
    )
    match_results = await match_uc.execute(profile)

    assert len(match_results) == 1
    assert match_results[0].mission.id == analyzed.id

    # Verify persistence
    persisted = await match_repo.get_by_user(profile.id)
    assert len(persisted) == 1
    assert persisted[0].analyzed_post_id == analyzed.id
    assert persisted[0].user_profile_id == profile.id

    # --- Step 3: GetTodayMissions reads the persisted matches ---
    get_uc = GetTodayMissions(
        mission_match_repository=match_repo,
        analyzed_post_repository=analyzed_repo,
        raw_post_repository=SqlAlchemyRawPostRepository(db_session),
    )
    today_missions = await get_uc.execute(
        GetTodayMissionsQuery(user_profile_id=profile.id, min_score=0.0)
    )

    assert len(today_missions) == 1
    result = today_missions[0]
    assert result.analyzed_post_id == analyzed.id
    assert result.raw_post_id == raw.id
    assert result.detected_contract_type == "freelance"
    assert result.detected_remote_mode == "full_remote"
    assert result.detected_tjm == 700.0
    assert result.global_score > 0.0
    assert "semantic" in result.score_details


@pytest.mark.asyncio
async def test_match_pipeline_reruns_upsert(db_session: AsyncSession) -> None:
    """Re-running MatchMissions on the same profile+mission replaces the previous score."""
    profile = make_user_profile(embedding=[1.0] * 384)
    raw = make_raw_post()
    analyzed = make_analyzed_post(raw_post_id=raw.id, embedding=[1.0] * 384)

    profile_repo = SqlAlchemyUserProfileRepository(db_session)
    raw_repo = SqlAlchemyRawPostRepository(db_session)
    analyzed_repo = SqlAlchemyAnalyzedPostRepository(db_session)
    search_query_repo = SqlAlchemySearchQueryRepository(db_session)
    link_repo = SqlAlchemySearchQueryRawPostRepository(db_session)
    match_repo = SqlAlchemyMissionMatchRepository(db_session)

    await profile_repo.save(profile)
    await raw_repo.save(raw)
    await analyzed_repo.save(analyzed)

    sq = SearchQuery(
        user_profile_id=profile.id, query="python", source="linkedin", limit=50
    )
    await search_query_repo.save_many([sq])
    await link_repo.save(SearchQueryRawPost(search_query_id=sq.id, raw_post_id=raw.id))

    gateway = _FakeEmbeddingGateway()
    scorer = MissionMatchScorer(gateway)

    def _make_uc() -> MatchMissions:
        return MatchMissions(
            scorer=scorer,
            search_query_repository=search_query_repo,
            search_query_raw_post_repository=link_repo,
            analyzed_post_repository=analyzed_repo,
            mission_match_repository=match_repo,
            min_score=0.0,
        )

    await _make_uc().execute(profile)
    await _make_uc().execute(profile)

    # Only one row per (user, mission) pair — upsert
    persisted = await match_repo.get_by_user(profile.id)
    assert len(persisted) == 1
