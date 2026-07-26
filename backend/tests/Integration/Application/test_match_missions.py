"""Integration test for MatchMissions — real scorer, real embeddings, no DB."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from src.Application.UseCase.match_missions import MatchMissions
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.Entity.search_query import SearchQuery
from src.Domain.Entity.search_query_raw_post import SearchQueryRawPost
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.search_query_raw_post_repository import SearchQueryRawPostRepository
from src.Domain.Repository.search_query_repository import SearchQueryRepository
from src.Domain.Service.mission_match_scorer import MissionMatchScorer
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack
from src.Infrastructure.External.Embedding.sentence_transformer_embedding_gateway import (
    SentenceTransformerEmbeddingGateway,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeSearchQueryRepository(SearchQueryRepository):
    def __init__(self, queries: list[SearchQuery]) -> None:
        self._queries = queries

    async def save_many(self, queries: list[SearchQuery]) -> None:
        raise NotImplementedError

    async def delete_by_profile(self, user_profile_id: UUID) -> None:
        raise NotImplementedError

    async def get_by_profile(self, user_profile_id: UUID) -> list[SearchQuery]:
        return [q for q in self._queries if q.user_profile_id == user_profile_id]

    async def get_by_source(self, source: str) -> list[SearchQuery]:
        raise NotImplementedError


class FakeSearchQueryRawPostRepository(SearchQueryRawPostRepository):
    def __init__(self, links: list[SearchQueryRawPost]) -> None:
        self._links = links

    async def save(self, link: SearchQueryRawPost) -> None:
        raise NotImplementedError

    async def exists(self, search_query_id: UUID, raw_post_id: UUID) -> bool:
        raise NotImplementedError

    async def find_by_search_query_id(self, search_query_id: UUID) -> list[SearchQueryRawPost]:
        raise NotImplementedError

    async def find_by_raw_post_id(self, raw_post_id: UUID) -> list[SearchQueryRawPost]:
        raise NotImplementedError

    async def find_by_search_query_ids(
        self, search_query_ids: list[UUID]
    ) -> list[SearchQueryRawPost]:
        return [lnk for lnk in self._links if lnk.search_query_id in search_query_ids]


class FakeAnalyzedPostRepository(AnalyzedPostRepository):
    def __init__(self, posts: list[AnalyzedPost]) -> None:
        self._posts = posts

    async def save(self, analyzed_post: AnalyzedPost) -> None:
        self._posts.append(analyzed_post)

    async def get_by_id(self, post_id: UUID) -> Optional[AnalyzedPost]:
        return next((p for p in self._posts if p.id == post_id), None)

    async def get_by_raw_post_id(self, raw_post_id: UUID) -> Optional[AnalyzedPost]:
        return None

    async def list_today_missions(self) -> list[AnalyzedPost]:
        return list(self._posts)

    async def list_missions(self, limit: int) -> list[AnalyzedPost]:
        return self._posts[:limit]

    async def find_by_raw_post_ids(self, raw_post_ids: list[UUID]) -> list[AnalyzedPost]:
        return [p for p in self._posts if p.raw_post_id in raw_post_ids]

    async def find_by_ids(self, ids: list[UUID]) -> list[AnalyzedPost]:
        return [p for p in self._posts if p.id in ids]


class FakeMissionMatchRepository(MissionMatchRepository):
    def __init__(self) -> None:
        self._matches: list[MissionMatch] = []
        self.save_many_calls: list[list[MissionMatch]] = []

    async def save(self, match: MissionMatch) -> None:
        self._matches.append(match)

    async def save_many(self, matches: list[MissionMatch]) -> None:
        self.save_many_calls.append(list(matches))
        self._matches.extend(matches)

    async def get_by_id(self, match_id: UUID) -> Optional[MissionMatch]:
        return next((m for m in self._matches if m.id == match_id), None)

    async def get_by_user(self, user_id: UUID) -> list[MissionMatch]:
        return [m for m in self._matches if m.user_profile_id == user_id]

    async def get_by_post(self, post_id: UUID) -> list[MissionMatch]:
        return [m for m in self._matches if m.analyzed_post_id == post_id]

    async def get_best_matches(self, user_id: UUID, limit: int) -> list[MissionMatch]:
        matches = [m for m in self._matches if m.user_profile_id == user_id]
        return sorted(matches, key=lambda m: m.final_score, reverse=True)[:limit]

    async def delete_user_matches(self, user_id: UUID) -> None:
        self._matches = [m for m in self._matches if m.user_profile_id != user_id]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_python_developer_ranked_above_accountant() -> None:
    """A Python dev profile should score higher on a Python mission than an Accountant one."""
    gateway = SentenceTransformerEmbeddingGateway()
    scorer = MissionMatchScorer(gateway)
    match_repo = FakeMissionMatchRepository()

    python_text = "Senior Python Developer FastAPI Django backend microservices REST API freelance"
    accountant_text = "Chartered Accountant finance Excel bookkeeping audit tax compliance permanent"
    profile_text = "Python developer FastAPI Django microservices backend 10 years freelance full remote"

    python_post = AnalyzedPost(
        raw_post_id=uuid4(),
        summary=python_text,
        detected_stack=("python", "fastapi", "django"),
        detected_contract_type=ContractType.FREELANCE,
        detected_remote_mode=RemoteMode.FULL_REMOTE,
        embedding=await gateway.embed_text(python_text),
    )
    accountant_post = AnalyzedPost(
        raw_post_id=uuid4(),
        summary=accountant_text,
        detected_stack=("excel",),
        detected_contract_type=ContractType.PERMANENT,
        detected_remote_mode=RemoteMode.ONSITE,
        embedding=await gateway.embed_text(accountant_text),
    )

    profile = UserProfile(
        email="python@test.com",
        full_name="Python Dev",
        title="Senior Python Developer",
        years_experience=10,
        preferred_contract_type=ContractType.FREELANCE,
        target_tjm=700.0,
        preferred_remote_mode=RemoteMode.FULL_REMOTE,
        skills=Stack.from_list(["python", "fastapi", "django"]),
        availability=datetime(2026, 9, 1, tzinfo=timezone.utc),
        embedding=await gateway.embed_text(profile_text),
    )

    sq = SearchQuery(
        user_profile_id=profile.id,
        query="python freelance",
        source="linkedin",
        limit=50,
    )
    links = [
        SearchQueryRawPost(search_query_id=sq.id, raw_post_id=python_post.raw_post_id),
        SearchQueryRawPost(search_query_id=sq.id, raw_post_id=accountant_post.raw_post_id),
    ]

    uc = MatchMissions(
        scorer=scorer,
        search_query_repository=FakeSearchQueryRepository([sq]),
        search_query_raw_post_repository=FakeSearchQueryRawPostRepository(links),
        analyzed_post_repository=FakeAnalyzedPostRepository([python_post, accountant_post]),
        mission_match_repository=match_repo,
        min_score=0.0,
    )

    results = await uc.execute(profile)

    assert len(results) == 2
    assert results[0].mission.id == python_post.id, (
        f"Expected Python mission first, got score "
        f"python={results[0].match_score.final_score:.3f} "
        f"vs accountant={results[1].match_score.final_score:.3f}"
    )
    # Both missions are persisted
    assert len(match_repo.save_many_calls) == 1
    assert len(match_repo.save_many_calls[0]) == 2


async def test_user_scoped_only_profile_missions_scored() -> None:
    """MatchMissions ne score que les missions liées au profil via SearchQuery."""
    gateway = SentenceTransformerEmbeddingGateway()
    scorer = MissionMatchScorer(gateway)
    match_repo = FakeMissionMatchRepository()

    python_text = "Senior Python Developer FastAPI backend freelance"
    accountant_text = "Chartered Accountant finance Excel audit permanent"
    profile_text = "Python developer FastAPI backend 10 years freelance full remote"

    python_post = AnalyzedPost(
        raw_post_id=uuid4(),
        summary=python_text,
        detected_stack=("python", "fastapi"),
        detected_contract_type=ContractType.FREELANCE,
        detected_remote_mode=RemoteMode.FULL_REMOTE,
        embedding=await gateway.embed_text(python_text),
    )
    # Ce post n'est PAS lié au profil via SearchQuery
    unlinked_post = AnalyzedPost(
        raw_post_id=uuid4(),
        summary=accountant_text,
        detected_stack=("excel",),
        detected_contract_type=ContractType.PERMANENT,
        detected_remote_mode=RemoteMode.ONSITE,
        embedding=await gateway.embed_text(accountant_text),
    )

    profile = UserProfile(
        email="scoped@test.com",
        full_name="Python Dev",
        title="Senior Python Developer",
        years_experience=10,
        preferred_contract_type=ContractType.FREELANCE,
        target_tjm=700.0,
        preferred_remote_mode=RemoteMode.FULL_REMOTE,
        skills=Stack.from_list(["python", "fastapi"]),
        availability=datetime(2026, 9, 1, tzinfo=timezone.utc),
        embedding=await gateway.embed_text(profile_text),
    )

    sq = SearchQuery(
        user_profile_id=profile.id,
        query="python freelance",
        source="linkedin",
        limit=50,
    )
    # Seul python_post est lié au profil
    links = [SearchQueryRawPost(search_query_id=sq.id, raw_post_id=python_post.raw_post_id)]

    uc = MatchMissions(
        scorer=scorer,
        search_query_repository=FakeSearchQueryRepository([sq]),
        search_query_raw_post_repository=FakeSearchQueryRawPostRepository(links),
        analyzed_post_repository=FakeAnalyzedPostRepository([python_post, unlinked_post]),
        mission_match_repository=match_repo,
        min_score=0.0,
    )

    results = await uc.execute(profile)

    assert len(results) == 1
    assert results[0].mission.id == python_post.id
    # Only the linked post is persisted
    assert len(match_repo.save_many_calls[0]) == 1
    assert match_repo.save_many_calls[0][0].analyzed_post_id == python_post.id
