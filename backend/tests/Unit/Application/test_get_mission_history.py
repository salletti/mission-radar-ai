"""Unit tests for GetMissionHistory use case — no I/O, no DB, no external services."""
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID, uuid4

from src.Application.DTO.get_mission_history_query import GetMissionHistoryQuery
from src.Application.DTO.today_mission import TodayMission
from src.Application.UseCase.get_mission_history import GetMissionHistory
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.mission_match import MissionMatch as MissionMatchEntity
from src.Domain.Entity.raw_post import RawPost
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.raw_post_repository import RawPostRepository
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.match_score import MatchScore
from src.Domain.ValueObject.remote_mode import RemoteMode

_BASE_TIME = datetime(2026, 6, 20, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fake implementations (minimal, reuse pattern from test_get_today_missions)
# ---------------------------------------------------------------------------


class FakeMissionMatchRepository(MissionMatchRepository):
    def __init__(self, matches: Optional[list[MissionMatchEntity]] = None) -> None:
        self._matches = matches or []

    async def save(self, match: MissionMatchEntity) -> None:
        self._matches.append(match)

    async def save_many(self, matches: list[MissionMatchEntity]) -> None:
        self._matches.extend(matches)

    async def get_by_id(self, match_id: UUID) -> Optional[MissionMatchEntity]:
        return next((m for m in self._matches if m.id == match_id), None)

    async def get_by_user(self, user_id: UUID) -> list[MissionMatchEntity]:
        return [m for m in self._matches if m.user_profile_id == user_id]

    async def get_by_post(self, post_id: UUID) -> list[MissionMatchEntity]:
        return [m for m in self._matches if m.analyzed_post_id == post_id]

    async def get_best_matches(self, user_id: UUID, limit: int) -> list[MissionMatchEntity]:
        matches = [m for m in self._matches if m.user_profile_id == user_id]
        return sorted(matches, key=lambda m: m.final_score, reverse=True)[:limit]

    async def delete_user_matches(self, user_id: UUID) -> None:
        self._matches = [m for m in self._matches if m.user_profile_id != user_id]


class FakeAnalyzedPostRepository(AnalyzedPostRepository):
    def __init__(self, posts: Optional[list[AnalyzedPost]] = None) -> None:
        self._posts: dict[UUID, AnalyzedPost] = {p.id: p for p in (posts or [])}

    async def save(self, analyzed_post: AnalyzedPost) -> None:
        self._posts[analyzed_post.id] = analyzed_post

    async def get_by_id(self, post_id: UUID) -> Optional[AnalyzedPost]:
        return self._posts.get(post_id)

    async def get_by_raw_post_id(self, raw_post_id: UUID) -> Optional[AnalyzedPost]:
        return next((p for p in self._posts.values() if p.raw_post_id == raw_post_id), None)

    async def list_today_missions(self) -> list[AnalyzedPost]:
        return list(self._posts.values())

    async def list_missions(self, limit: int) -> list[AnalyzedPost]:
        return list(self._posts.values())[:limit]

    async def find_by_raw_post_ids(self, raw_post_ids: list[UUID]) -> list[AnalyzedPost]:
        return [p for p in self._posts.values() if p.raw_post_id in raw_post_ids]

    async def find_by_ids(self, ids: list[UUID]) -> list[AnalyzedPost]:
        return [p for p in self._posts.values() if p.id in ids]


class FakeRawPostRepository(RawPostRepository):
    def __init__(self, posts: Optional[list[RawPost]] = None) -> None:
        self._posts: dict[UUID, RawPost] = {p.id: p for p in (posts or [])}

    async def save(self, raw_post: RawPost) -> None:
        self._posts[raw_post.id] = raw_post

    async def exists_by_external_id(self, source: str, external_id: str) -> bool:
        return any(p.source == source and p.external_id == external_id for p in self._posts.values())

    async def get_by_id(self, raw_post_id: UUID) -> Optional[RawPost]:
        return self._posts.get(raw_post_id)

    async def save_many(self, posts: list[RawPost]) -> None:
        for p in posts:
            self._posts[p.id] = p

    async def get_by_source_and_external_id(self, source: str, external_id: str) -> Optional[RawPost]:
        return next(
            (p for p in self._posts.values() if p.source == source and p.external_id == external_id),
            None,
        )

    async def list_recent(self, limit: int) -> list[RawPost]:
        return list(self._posts.values())[:limit]

    async def find_by_ids(self, ids: list[UUID]) -> list[RawPost]:
        return [p for p in self._posts.values() if p.id in ids]


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_raw_post() -> RawPost:
    uid = uuid4()
    return RawPost(
        source="linkedin",
        external_id=str(uid),
        author_name="Alice",
        author_url="https://linkedin.com/in/alice",
        content="Mission Python FastAPI",
        post_url=f"https://linkedin.com/posts/{uid}",
        published_at=_BASE_TIME,
        scraped_at=_BASE_TIME,
    )


def _make_analyzed_post(raw_post_id: UUID) -> AnalyzedPost:
    return AnalyzedPost(
        raw_post_id=raw_post_id,
        summary="Mission Python.",
        detected_stack=("python",),
        detected_contract_type=ContractType.FREELANCE,
        detected_remote_mode=RemoteMode.FULL_REMOTE,
    )


def _make_match(
    user_profile_id: UUID,
    analyzed_post_id: UUID,
    score: float,
    created_at: datetime,
) -> MissionMatchEntity:
    match = MissionMatchEntity.create(
        user_profile_id=user_profile_id,
        analyzed_post_id=analyzed_post_id,
        match_score=MatchScore(
            semantic_score=score,
            contract_score=score,
            remote_score=score,
            tjm_score=score,
        ),
    )
    object.__setattr__(match, "created_at", created_at)
    return match


def _build_scenario(
    user_id: UUID,
    scores_and_offsets: list[tuple[float, int]],
) -> tuple[FakeMissionMatchRepository, FakeAnalyzedPostRepository, FakeRawPostRepository]:
    raws, analyzed_list, matches = [], [], []
    for score, day_offset in scores_and_offsets:
        raw = _make_raw_post()
        analyzed = _make_analyzed_post(raw.id)
        match = _make_match(
            user_id,
            analyzed.id,
            score,
            _BASE_TIME + timedelta(days=day_offset),
        )
        raws.append(raw)
        analyzed_list.append(analyzed)
        matches.append(match)
    return (
        FakeMissionMatchRepository(matches),
        FakeAnalyzedPostRepository(analyzed_list),
        FakeRawPostRepository(raws),
    )


def _make_use_case(
    match_repo: FakeMissionMatchRepository,
    analyzed_repo: FakeAnalyzedPostRepository,
    raw_repo: FakeRawPostRepository,
) -> GetMissionHistory:
    return GetMissionHistory(match_repo, analyzed_repo, raw_repo)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_get_mission_history_sorted_by_created_at_descending() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(
        user_id, [(0.7, 0), (0.8, 2), (0.6, 1)]
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(GetMissionHistoryQuery(user_profile_id=user_id))

    created_ats = [r.mission_match_id for r in results]
    matches = await match_repo.get_by_user(user_id)
    match_map = {m.id: m.created_at for m in matches}
    dates = [match_map[mid] for mid in created_ats]
    assert dates == sorted(dates, reverse=True)


async def test_get_mission_history_filters_by_min_score() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(
        user_id, [(0.9, 0), (0.3, 1), (0.7, 2)]
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(GetMissionHistoryQuery(user_profile_id=user_id, min_score=0.6))

    assert len(results) == 2
    assert all(r.global_score >= 0.6 for r in results)


async def test_get_mission_history_applies_limit() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(
        user_id, [(0.8, i) for i in range(10)]
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(GetMissionHistoryQuery(user_profile_id=user_id, limit=3))

    assert len(results) == 3


async def test_get_mission_history_applies_offset() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(
        user_id, [(0.8, i) for i in range(5)]
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    all_results = await uc.execute(GetMissionHistoryQuery(user_profile_id=user_id, limit=5))
    paged_results = await uc.execute(
        GetMissionHistoryQuery(user_profile_id=user_id, limit=5, offset=2)
    )

    assert len(paged_results) == 3
    assert paged_results[0].mission_match_id == all_results[2].mission_match_id


async def test_get_mission_history_empty_when_no_matches() -> None:
    user_id = uuid4()
    uc = _make_use_case(
        FakeMissionMatchRepository([]),
        FakeAnalyzedPostRepository([]),
        FakeRawPostRepository([]),
    )

    results = await uc.execute(GetMissionHistoryQuery(user_profile_id=user_id))

    assert results == []


async def test_get_mission_history_returns_today_mission_dto() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(user_id, [(0.8, 0)])
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(GetMissionHistoryQuery(user_profile_id=user_id))

    assert len(results) == 1
    assert isinstance(results[0], TodayMission)
