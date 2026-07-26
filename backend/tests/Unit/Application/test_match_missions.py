"""Unit tests for MatchMissions use case — no I/O, no DB, no external services."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.Exception.application_error import ProfileEmbeddingMissingError
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
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.match_score import MatchScore
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack

_AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)
_DEFAULT_EMBEDDING: list[float] = [0.1] * 384


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeMissionMatchScorer:
    def __init__(self, scores: dict[UUID, float] | None = None) -> None:
        self._scores = scores or {}
        self.calls: list[tuple[UserProfile, AnalyzedPost]] = []

    async def calculate(self, profile: UserProfile, mission: AnalyzedPost) -> MatchScore:
        self.calls.append((profile, mission))
        s = self._scores.get(mission.id, 0.5)
        # identical value on all 4 components → final_score == s (weights sum to 1.0)
        return MatchScore(semantic_score=s, contract_score=s, remote_score=s, tjm_score=s)


class FakeMissionMatchRepository(MissionMatchRepository):
    def __init__(self) -> None:
        self._matches: list[MissionMatch] = []
        self.save_many_calls: list[list[MissionMatch]] = []
        self.delete_calls: list[UUID] = []

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
        self.delete_calls.append(user_id)
        self._matches = [m for m in self._matches if m.user_profile_id != user_id]


class FakeSearchQueryRepository(SearchQueryRepository):
    def __init__(self, queries: list[SearchQuery] | None = None) -> None:
        self._queries = queries or []

    async def save_many(self, queries: list[SearchQuery]) -> None:
        raise NotImplementedError

    async def delete_by_profile(self, user_profile_id: UUID) -> None:
        raise NotImplementedError

    async def get_by_profile(self, user_profile_id: UUID) -> list[SearchQuery]:
        return [q for q in self._queries if q.user_profile_id == user_profile_id]

    async def get_by_source(self, source: str) -> list[SearchQuery]:
        raise NotImplementedError


class FakeSearchQueryRawPostRepository(SearchQueryRawPostRepository):
    def __init__(self, links: list[SearchQueryRawPost] | None = None) -> None:
        self._links = links or []

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
    def __init__(self, posts: list[AnalyzedPost] | None = None) -> None:
        self._posts = posts or []

    async def save(self, analyzed_post: AnalyzedPost) -> None:
        self._posts.append(analyzed_post)

    async def get_by_id(self, post_id: UUID) -> Optional[AnalyzedPost]:
        return next((p for p in self._posts if p.id == post_id), None)

    async def get_by_raw_post_id(self, raw_post_id: UUID) -> Optional[AnalyzedPost]:
        return next((p for p in self._posts if p.raw_post_id == raw_post_id), None)

    async def list_today_missions(self) -> list[AnalyzedPost]:
        return list(self._posts)

    async def list_missions(self, limit: int) -> list[AnalyzedPost]:
        return self._posts[:limit]

    async def find_by_raw_post_ids(self, raw_post_ids: list[UUID]) -> list[AnalyzedPost]:
        return [p for p in self._posts if p.raw_post_id in raw_post_ids]

    async def find_by_ids(self, ids: list[UUID]) -> list[AnalyzedPost]:
        return [p for p in self._posts if p.id in ids]


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_profile(**kwargs) -> UserProfile:
    defaults: dict = {
        "email": f"{uuid4()}@test.com",
        "full_name": "Test User",
        "title": "Senior Python Engineer",
        "years_experience": 10,
        "preferred_contract_type": ContractType.FREELANCE,
        "target_tjm": 700.0,
        "preferred_remote_mode": RemoteMode.FULL_REMOTE,
        "skills": Stack.from_list(["python", "fastapi"]),
        "availability": _AVAILABILITY,
        "embedding": _DEFAULT_EMBEDDING,
    }
    return UserProfile(**{**defaults, **kwargs})


def _make_mission(**kwargs) -> AnalyzedPost:
    defaults: dict = {
        "raw_post_id": uuid4(),
        "summary": "Mission Python full remote.",
        "detected_stack": ("fastapi", "python"),
        "detected_contract_type": ContractType.FREELANCE,
        "detected_remote_mode": RemoteMode.FULL_REMOTE,
        "detected_tjm": 700.0,
        "embedding": [0.5] * 384,
    }
    return AnalyzedPost(**{**defaults, **kwargs})


def _make_search_query(profile_id: UUID) -> SearchQuery:
    return SearchQuery(
        user_profile_id=profile_id,
        query="python freelance",
        source="linkedin",
        limit=50,
    )


def _make_link(search_query_id: UUID, raw_post_id: UUID) -> SearchQueryRawPost:
    return SearchQueryRawPost(search_query_id=search_query_id, raw_post_id=raw_post_id)


def _make_use_case(
    profile: UserProfile,
    missions: list[AnalyzedPost] | None = None,
    queries: list[SearchQuery] | None = None,
    links: list[SearchQueryRawPost] | None = None,
    scores: dict[UUID, float] | None = None,
    min_score: float = 0.50,
    top_n: int = 20,
) -> tuple[MatchMissions, FakeMissionMatchScorer, FakeMissionMatchRepository]:
    scorer = FakeMissionMatchScorer(scores)
    match_repo = FakeMissionMatchRepository()
    uc = MatchMissions(
        scorer=scorer,
        search_query_repository=FakeSearchQueryRepository(queries),
        search_query_raw_post_repository=FakeSearchQueryRawPostRepository(links),
        analyzed_post_repository=FakeAnalyzedPostRepository(missions),
        mission_match_repository=match_repo,
        min_score=min_score,
        top_n=top_n,
    )
    return uc, scorer, match_repo


# ---------------------------------------------------------------------------
# Tests — comportements existants conservés
# ---------------------------------------------------------------------------


async def test_results_sorted_descending() -> None:
    profile = _make_profile()
    m1, m2, m3 = _make_mission(), _make_mission(), _make_mission()
    sq = _make_search_query(profile.id)
    links = [
        _make_link(sq.id, m1.raw_post_id),
        _make_link(sq.id, m2.raw_post_id),
        _make_link(sq.id, m3.raw_post_id),
    ]
    uc, _, _ = _make_use_case(
        profile=profile,
        missions=[m1, m2, m3],
        queries=[sq],
        links=links,
        scores={m1.id: 0.60, m2.id: 0.95, m3.id: 0.80},
    )

    results = await uc.execute(profile)

    assert len(results) == 3
    assert results[0].mission.id == m2.id  # 0.95
    assert results[1].mission.id == m3.id  # 0.80
    assert results[2].mission.id == m1.id  # 0.60


async def test_mission_below_threshold_excluded() -> None:
    profile = _make_profile()
    m = _make_mission()
    sq = _make_search_query(profile.id)
    uc, _, _ = _make_use_case(
        profile=profile,
        missions=[m],
        queries=[sq],
        links=[_make_link(sq.id, m.raw_post_id)],
        scores={m.id: 0.40},
    )

    results = await uc.execute(profile)

    assert results == []


async def test_mission_without_embedding_ignored() -> None:
    profile = _make_profile()
    m_no_emb = _make_mission(embedding=None)
    m_with_emb = _make_mission()
    sq = _make_search_query(profile.id)
    links = [
        _make_link(sq.id, m_no_emb.raw_post_id),
        _make_link(sq.id, m_with_emb.raw_post_id),
    ]
    uc, scorer, _ = _make_use_case(
        profile=profile,
        missions=[m_no_emb, m_with_emb],
        queries=[sq],
        links=links,
        scores={m_with_emb.id: 0.80},
    )

    results = await uc.execute(profile)

    assert len(results) == 1
    assert results[0].mission.id == m_with_emb.id
    assert all(call[1].id != m_no_emb.id for call in scorer.calls)


async def test_profile_without_embedding_raises() -> None:
    profile = _make_profile(embedding=None)
    uc, _, _ = _make_use_case(profile=profile)

    with pytest.raises(ProfileEmbeddingMissingError):
        await uc.execute(profile)


async def test_result_capped_at_top_n() -> None:
    profile = _make_profile()
    missions = [_make_mission() for _ in range(25)]
    sq = _make_search_query(profile.id)
    links = [_make_link(sq.id, m.raw_post_id) for m in missions]
    scores = {m.id: 0.80 for m in missions}
    uc, _, _ = _make_use_case(
        profile=profile,
        missions=missions,
        queries=[sq],
        links=links,
        scores=scores,
        top_n=20,
    )

    results = await uc.execute(profile)

    assert len(results) == 20


# ---------------------------------------------------------------------------
# Tests — user-scoped
# ---------------------------------------------------------------------------


async def test_two_queries_three_missions() -> None:
    """2 SearchQuery distincts → 3 missions distinctes toutes scorées."""
    profile = _make_profile()
    m1, m2, m3 = _make_mission(), _make_mission(), _make_mission()
    sq1 = _make_search_query(profile.id)
    sq2 = _make_search_query(profile.id)
    links = [
        _make_link(sq1.id, m1.raw_post_id),
        _make_link(sq1.id, m2.raw_post_id),
        _make_link(sq2.id, m3.raw_post_id),
    ]
    uc, scorer, _ = _make_use_case(
        profile=profile,
        missions=[m1, m2, m3],
        queries=[sq1, sq2],
        links=links,
        scores={m1.id: 0.70, m2.id: 0.80, m3.id: 0.90},
    )

    results = await uc.execute(profile)

    assert len(results) == 3
    assert len(scorer.calls) == 3


async def test_deduplication_same_raw_post() -> None:
    """Même RawPost découvert par 2 SearchQuery → scorer appelé une seule fois."""
    profile = _make_profile()
    m = _make_mission()
    sq1 = _make_search_query(profile.id)
    sq2 = _make_search_query(profile.id)
    links = [
        _make_link(sq1.id, m.raw_post_id),
        _make_link(sq2.id, m.raw_post_id),  # même raw_post_id
    ]
    uc, scorer, _ = _make_use_case(
        profile=profile,
        missions=[m],
        queries=[sq1, sq2],
        links=links,
        scores={m.id: 0.75},
    )

    results = await uc.execute(profile)

    assert len(results) == 1
    assert len(scorer.calls) == 1


async def test_no_search_query_returns_empty() -> None:
    """Aucun SearchQuery pour ce profil → liste vide."""
    profile = _make_profile()
    m = _make_mission()
    uc, scorer, _ = _make_use_case(
        profile=profile,
        missions=[m],
        queries=[],
        links=[],
    )

    results = await uc.execute(profile)

    assert results == []
    assert scorer.calls == []


async def test_no_links_returns_empty() -> None:
    """SearchQuery présents mais aucun lien vers un RawPost → liste vide."""
    profile = _make_profile()
    m = _make_mission()
    sq = _make_search_query(profile.id)
    uc, scorer, _ = _make_use_case(
        profile=profile,
        missions=[m],
        queries=[sq],
        links=[],
    )

    results = await uc.execute(profile)

    assert results == []
    assert scorer.calls == []


async def test_no_analyzed_post_returns_empty() -> None:
    """Liens présents mais aucun AnalyzedPost correspondant → liste vide."""
    profile = _make_profile()
    sq = _make_search_query(profile.id)
    orphan_raw_post_id = uuid4()
    links = [_make_link(sq.id, orphan_raw_post_id)]
    uc, scorer, _ = _make_use_case(
        profile=profile,
        missions=[],  # aucun AnalyzedPost en base
        queries=[sq],
        links=links,
    )

    results = await uc.execute(profile)

    assert results == []
    assert scorer.calls == []


# ---------------------------------------------------------------------------
# Tests — persistence
# ---------------------------------------------------------------------------


async def test_save_many_called_with_all_scored_missions() -> None:
    """save_many reçoit un MissionMatch pour chaque mission scorée, avant filtrage."""
    profile = _make_profile()
    m_high = _make_mission()
    m_low = _make_mission()
    sq = _make_search_query(profile.id)
    links = [
        _make_link(sq.id, m_high.raw_post_id),
        _make_link(sq.id, m_low.raw_post_id),
    ]
    uc, _, match_repo = _make_use_case(
        profile=profile,
        missions=[m_high, m_low],
        queries=[sq],
        links=links,
        scores={m_high.id: 0.90, m_low.id: 0.20},  # m_low below default min_score 0.50
        min_score=0.50,
    )

    results = await uc.execute(profile)

    # Only 1 result returned (m_low filtered out)
    assert len(results) == 1
    # But save_many received both MissionMatch entities
    assert len(match_repo.save_many_calls) == 1
    saved = match_repo.save_many_calls[0]
    assert len(saved) == 2
    saved_post_ids = {m.analyzed_post_id for m in saved}
    assert m_high.id in saved_post_ids
    assert m_low.id in saved_post_ids


async def test_save_many_not_called_when_no_queries() -> None:
    """Pas de SearchQuery → delete ni save_many jamais appelés."""
    profile = _make_profile()
    uc, _, match_repo = _make_use_case(
        profile=profile,
        missions=[],
        queries=[],
        links=[],
    )

    await uc.execute(profile)

    assert match_repo.save_many_calls == []
    assert match_repo.delete_calls == []


async def test_delete_called_before_save_many() -> None:
    """delete_user_matches est appelé avant save_many pour garantir un remplacement propre."""
    profile = _make_profile()
    m = _make_mission()
    sq = _make_search_query(profile.id)
    uc, _, match_repo = _make_use_case(
        profile=profile,
        missions=[m],
        queries=[sq],
        links=[_make_link(sq.id, m.raw_post_id)],
        scores={m.id: 0.80},
    )

    await uc.execute(profile)

    assert match_repo.delete_calls == [profile.id]
    assert len(match_repo.save_many_calls) == 1


async def test_save_many_mission_match_has_correct_ids() -> None:
    """Les MissionMatch persistés référencent le bon profil et la bonne mission."""
    profile = _make_profile()
    m = _make_mission()
    sq = _make_search_query(profile.id)
    uc, _, match_repo = _make_use_case(
        profile=profile,
        missions=[m],
        queries=[sq],
        links=[_make_link(sq.id, m.raw_post_id)],
        scores={m.id: 0.80},
    )

    await uc.execute(profile)

    saved = match_repo.save_many_calls[0]
    assert len(saved) == 1
    assert saved[0].user_profile_id == profile.id
    assert saved[0].analyzed_post_id == m.id
    assert saved[0].match_score.final_score == pytest.approx(0.80)
