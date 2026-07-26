"""Unit tests for GetTodayMissions use case — no I/O, no DB, no external services."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from src.Application.DTO.get_today_missions_query import GetTodayMissionsQuery
from src.Application.DTO.today_mission import TodayMission
from src.Application.UseCase.get_today_missions import GetTodayMissions
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.mission_match import MissionMatch as MissionMatchEntity
from src.Domain.Entity.raw_post import RawPost
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.raw_post_repository import RawPostRepository
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.match_score import MatchScore
from src.Domain.ValueObject.remote_mode import RemoteMode

_NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Fake implementations
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
        return any(
            p.source == source and p.external_id == external_id
            for p in self._posts.values()
        )

    async def get_by_id(self, raw_post_id: UUID) -> Optional[RawPost]:
        return self._posts.get(raw_post_id)

    async def save_many(self, posts: list[RawPost]) -> None:
        for post in posts:
            self._posts[post.id] = post

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
        author_name="Alice Recruiter",
        author_url="https://linkedin.com/in/alice",
        content="Mission Python FastAPI full remote 700€/j #freelance",
        post_url=f"https://linkedin.com/posts/{uid}",
        published_at=_NOW,
        scraped_at=_NOW,
    )


def _make_analyzed_post(raw_post_id: UUID) -> AnalyzedPost:
    return AnalyzedPost(
        raw_post_id=raw_post_id,
        summary="Mission Python full remote.",
        detected_stack=("fastapi", "python"),
        detected_contract_type=ContractType.FREELANCE,
        detected_remote_mode=RemoteMode.FULL_REMOTE,
        detected_tjm=700.0,
    )


def _make_match(
    user_profile_id: UUID,
    analyzed_post_id: UUID,
    score: float,
) -> MissionMatchEntity:
    match_score = MatchScore(
        semantic_score=score,
        contract_score=score,
        remote_score=score,
        tjm_score=score,
    )
    return MissionMatchEntity.create(
        user_profile_id=user_profile_id,
        analyzed_post_id=analyzed_post_id,
        match_score=match_score,
    )


def _build_scenario(
    user_id: UUID,
    scores: list[float],
) -> tuple[
    FakeMissionMatchRepository,
    FakeAnalyzedPostRepository,
    FakeRawPostRepository,
    list[MissionMatchEntity],
]:
    raw_posts: list[RawPost] = []
    analyzed_posts: list[AnalyzedPost] = []
    matches: list[MissionMatchEntity] = []

    for score in scores:
        raw = _make_raw_post()
        analyzed = _make_analyzed_post(raw.id)
        match = _make_match(user_id, analyzed.id, score)
        raw_posts.append(raw)
        analyzed_posts.append(analyzed)
        matches.append(match)

    return (
        FakeMissionMatchRepository(matches),
        FakeAnalyzedPostRepository(analyzed_posts),
        FakeRawPostRepository(raw_posts),
        matches,
    )


def _make_use_case(
    match_repo: FakeMissionMatchRepository,
    analyzed_repo: FakeAnalyzedPostRepository,
    raw_repo: FakeRawPostRepository,
) -> GetTodayMissions:
    return GetTodayMissions(match_repo, analyzed_repo, raw_repo)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_get_today_missions_sorted_descending() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, _ = _build_scenario(user_id, [0.6, 0.9, 0.75])
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(GetTodayMissionsQuery(user_profile_id=user_id))

    assert [r.global_score for r in results] == [0.9, 0.75, 0.6]


async def test_get_today_missions_filters_min_score() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, _ = _build_scenario(user_id, [0.9, 0.4, 0.7])
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(
        GetTodayMissionsQuery(user_profile_id=user_id, min_score=0.6)
    )

    assert all(r.global_score >= 0.6 for r in results)
    assert len(results) == 2


async def test_get_today_missions_respects_limit() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, _ = _build_scenario(
        user_id, [0.9, 0.85, 0.8, 0.75, 0.7]
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(
        GetTodayMissionsQuery(user_profile_id=user_id, min_score=0.0, limit=3)
    )

    assert len(results) == 3


async def test_get_today_missions_returns_today_mission_dto() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, _ = _build_scenario(user_id, [0.8])
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(GetTodayMissionsQuery(user_profile_id=user_id))

    assert len(results) == 1
    assert isinstance(results[0], TodayMission)
    assert results[0].detected_contract_type == "freelance"
    assert results[0].detected_remote_mode == "full_remote"
    assert results[0].detected_tjm == 700.0
    assert "semantic" in results[0].score_details
    assert hasattr(results[0], "title")
    assert hasattr(results[0], "company")
    assert hasattr(results[0], "location")


async def test_get_today_missions_empty_when_no_matches() -> None:
    user_id = uuid4()
    uc = _make_use_case(
        FakeMissionMatchRepository([]),
        FakeAnalyzedPostRepository([]),
        FakeRawPostRepository([]),
    )

    results = await uc.execute(GetTodayMissionsQuery(user_profile_id=user_id))

    assert results == []


async def test_get_today_missions_content_excerpt_truncated() -> None:
    user_id = uuid4()
    raw = RawPost(
        source="linkedin",
        external_id=str(uuid4()),
        author_name="Bob",
        author_url="https://linkedin.com/in/bob",
        content="x" * 500,
        post_url="https://linkedin.com/posts/1",
        published_at=_NOW,
        scraped_at=_NOW,
    )
    analyzed = _make_analyzed_post(raw.id)
    match = _make_match(user_id, analyzed.id, 0.9)

    uc = _make_use_case(
        FakeMissionMatchRepository([match]),
        FakeAnalyzedPostRepository([analyzed]),
        FakeRawPostRepository([raw]),
    )

    results = await uc.execute(GetTodayMissionsQuery(user_profile_id=user_id))

    assert len(results[0].content_excerpt) == 300


async def test_get_today_missions_skips_missing_analyzed_post() -> None:
    user_id = uuid4()
    analyzed_post_id = uuid4()
    match = _make_match(user_id, analyzed_post_id, 0.9)

    uc = _make_use_case(
        FakeMissionMatchRepository([match]),
        FakeAnalyzedPostRepository([]),  # no matching analyzed post
        FakeRawPostRepository([]),
    )

    results = await uc.execute(GetTodayMissionsQuery(user_profile_id=user_id))

    assert results == []
