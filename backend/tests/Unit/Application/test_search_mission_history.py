"""Unit tests for SearchMissionHistory use case — no I/O, no DB, no external services."""
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID, uuid4

from src.Application.DTO.search_mission_history_query import SearchMissionHistoryQuery
from src.Application.DTO.today_mission import TodayMission
from src.Application.UseCase.search_mission_history import SearchMissionHistory
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
# Fake implementations (same pattern as test_get_mission_history)
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


def _make_analyzed_post(
    raw_post_id: UUID,
    title: Optional[str] = None,
    company: Optional[str] = None,
    detected_stack: tuple[str, ...] = ("python",),
) -> AnalyzedPost:
    return AnalyzedPost(
        raw_post_id=raw_post_id,
        summary="Mission Python.",
        detected_stack=detected_stack,
        detected_contract_type=ContractType.FREELANCE,
        detected_remote_mode=RemoteMode.FULL_REMOTE,
        title=title,
        company=company,
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
    entries: list[dict],
) -> tuple[FakeMissionMatchRepository, FakeAnalyzedPostRepository, FakeRawPostRepository]:
    """Each entry: {score, day_offset, title?, company?, detected_stack?}."""
    raws, analyzed_list, matches = [], [], []
    for entry in entries:
        raw = _make_raw_post()
        analyzed = _make_analyzed_post(
            raw.id,
            title=entry.get("title"),
            company=entry.get("company"),
            detected_stack=entry.get("detected_stack", ("python",)),
        )
        match = _make_match(
            user_id,
            analyzed.id,
            entry["score"],
            _BASE_TIME + timedelta(days=entry["day_offset"]),
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
) -> SearchMissionHistory:
    return SearchMissionHistory(match_repo, analyzed_repo, raw_repo)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_search_without_keyword_returns_everything_paginated() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(
        user_id,
        [{"score": 0.8, "day_offset": i} for i in range(3)],
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(SearchMissionHistoryQuery(user_profile_id=user_id))

    assert len(results) == 3
    assert all(isinstance(r, TodayMission) for r in results)


async def test_search_matches_keyword_in_title() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(
        user_id,
        [
            {"score": 0.8, "day_offset": 0, "title": "Senior Kubernetes Engineer"},
            {"score": 0.8, "day_offset": 1, "title": "Frontend Developer"},
        ],
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(SearchMissionHistoryQuery(user_profile_id=user_id, keyword="kubernetes"))

    assert len(results) == 1
    assert results[0].title == "Senior Kubernetes Engineer"


async def test_search_matches_keyword_in_company() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(
        user_id,
        [
            {"score": 0.8, "day_offset": 0, "company": "Acme Corp"},
            {"score": 0.8, "day_offset": 1, "company": "Other Inc"},
        ],
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(SearchMissionHistoryQuery(user_profile_id=user_id, keyword="acme"))

    assert len(results) == 1
    assert results[0].company == "Acme Corp"


async def test_search_matches_keyword_in_detected_stack() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(
        user_id,
        [
            {"score": 0.8, "day_offset": 0, "detected_stack": ("kubernetes", "python")},
            {"score": 0.8, "day_offset": 1, "detected_stack": ("react", "typescript")},
        ],
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(SearchMissionHistoryQuery(user_profile_id=user_id, keyword="Kubernetes"))

    assert len(results) == 1
    assert "kubernetes" in results[0].detected_stack


async def test_search_keyword_is_case_insensitive() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(
        user_id,
        [{"score": 0.8, "day_offset": 0, "title": "Senior Python Engineer"}],
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(SearchMissionHistoryQuery(user_profile_id=user_id, keyword="PYTHON"))

    assert len(results) == 1


async def test_search_returns_empty_when_keyword_matches_nothing() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(
        user_id,
        [{"score": 0.8, "day_offset": 0, "title": "Senior Python Engineer"}],
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(SearchMissionHistoryQuery(user_profile_id=user_id, keyword="rust"))

    assert results == []


async def test_search_still_applies_min_score_and_pagination() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(
        user_id,
        [
            {"score": 0.9, "day_offset": 0, "title": "Python mission A"},
            {"score": 0.3, "day_offset": 1, "title": "Python mission B"},
            {"score": 0.7, "day_offset": 2, "title": "Python mission C"},
        ],
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    results = await uc.execute(
        SearchMissionHistoryQuery(user_profile_id=user_id, keyword="python", min_score=0.6, limit=1)
    )

    assert len(results) == 1
    assert results[0].global_score >= 0.6
