"""Unit tests for GetActivityHistory use case — no I/O, no DB, no external services."""
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.DTO.activity_event import ActivityEvent, ActivityHistoryPage
from src.Application.DTO.get_activity_history_query import GetActivityHistoryQuery
from src.Application.UseCase.get_activity_history import GetActivityHistory
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.digest_history import DigestHistory
from src.Domain.Entity.mission_match import MissionMatch as MissionMatchEntity
from src.Domain.Entity.raw_post import RawPost
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.digest_history_repository import DigestHistoryRepository
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


class FakeDigestHistoryRepository(DigestHistoryRepository):
    def __init__(self, entries: Optional[list[DigestHistory]] = None) -> None:
        self._entries = entries or []

    async def save(self, history: DigestHistory) -> None:
        self._entries.append(history)

    async def find_by_user(self, user_id: UUID) -> list[DigestHistory]:
        return [d for d in self._entries if d.user_id == user_id]


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_raw_post(content: str = "Mission Python FastAPI full remote 700€/j") -> RawPost:
    uid = uuid4()
    return RawPost(
        source="linkedin",
        external_id=str(uid),
        author_name="Alice Recruiter",
        author_url="https://linkedin.com/in/alice",
        content=content,
        post_url=f"https://linkedin.com/posts/{uid}",
        published_at=_BASE_TIME,
        scraped_at=_BASE_TIME,
    )


def _make_analyzed_post(
    raw_post_id: UUID,
    title: Optional[str] = "Senior Python Engineer",
    company: Optional[str] = "Acme Corp",
    summary: str = "Mission Python full remote.",
) -> AnalyzedPost:
    return AnalyzedPost(
        raw_post_id=raw_post_id,
        summary=summary,
        detected_stack=("python", "fastapi"),
        detected_contract_type=ContractType.FREELANCE,
        detected_remote_mode=RemoteMode.FULL_REMOTE,
        title=title,
        company=company,
    )


def _make_match(
    user_profile_id: UUID,
    analyzed_post_id: UUID,
    score: float = 0.8,
    created_at: Optional[datetime] = None,
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
    object.__setattr__(match, "created_at", created_at or _BASE_TIME)
    return match


def _build_scenario(
    user_id: UUID,
    count: int = 1,
    score: float = 0.8,
    day_offsets: Optional[list[int]] = None,
) -> tuple[FakeMissionMatchRepository, FakeAnalyzedPostRepository, FakeRawPostRepository]:
    offsets = day_offsets or list(range(count))
    raws, analyzed_list, matches = [], [], []
    for i in range(count):
        raw = _make_raw_post()
        analyzed = _make_analyzed_post(raw.id)
        match = _make_match(user_id, analyzed.id, score, _BASE_TIME + timedelta(days=offsets[i]))
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
    digests: Optional[list[DigestHistory]] = None,
) -> GetActivityHistory:
    return GetActivityHistory(match_repo, analyzed_repo, raw_repo, FakeDigestHistoryRepository(digests))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_activity_history_page_type() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(user_id, count=2)
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    result = await uc.execute(GetActivityHistoryQuery(user_profile_id=user_id))

    assert isinstance(result, ActivityHistoryPage)
    assert all(isinstance(item, ActivityEvent) for item in result.items)


@pytest.mark.asyncio
async def test_event_type_is_mission_match() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(user_id, count=1)
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    result = await uc.execute(GetActivityHistoryQuery(user_profile_id=user_id))

    assert result.items[0].type == "MISSION_MATCH"


@pytest.mark.asyncio
async def test_score_is_converted_to_0_100_range() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(user_id, count=1, score=0.85)
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    result = await uc.execute(GetActivityHistoryQuery(user_profile_id=user_id))

    assert result.items[0].score == 85


@pytest.mark.asyncio
async def test_title_uses_analyzed_post_title() -> None:
    user_id = uuid4()
    raw = _make_raw_post()
    analyzed = _make_analyzed_post(raw.id, title="Backend Python Expert", company="StartupX")
    match = _make_match(user_id, analyzed.id)
    uc = _make_use_case(
        FakeMissionMatchRepository([match]),
        FakeAnalyzedPostRepository([analyzed]),
        FakeRawPostRepository([raw]),
    )

    result = await uc.execute(GetActivityHistoryQuery(user_profile_id=user_id))

    assert result.items[0].title == "Backend Python Expert"


@pytest.mark.asyncio
async def test_title_falls_back_to_company_when_no_title() -> None:
    user_id = uuid4()
    raw = _make_raw_post()
    analyzed = _make_analyzed_post(raw.id, title=None, company="Acme Corp")
    match = _make_match(user_id, analyzed.id)
    uc = _make_use_case(
        FakeMissionMatchRepository([match]),
        FakeAnalyzedPostRepository([analyzed]),
        FakeRawPostRepository([raw]),
    )

    result = await uc.execute(GetActivityHistoryQuery(user_profile_id=user_id))

    assert result.items[0].title == "Acme Corp"


@pytest.mark.asyncio
async def test_title_falls_back_to_author_when_no_title_no_company() -> None:
    user_id = uuid4()
    raw = _make_raw_post()
    analyzed = _make_analyzed_post(raw.id, title=None, company=None)
    match = _make_match(user_id, analyzed.id)
    uc = _make_use_case(
        FakeMissionMatchRepository([match]),
        FakeAnalyzedPostRepository([analyzed]),
        FakeRawPostRepository([raw]),
    )

    result = await uc.execute(GetActivityHistoryQuery(user_profile_id=user_id))

    assert result.items[0].title == "Mission de Alice Recruiter"


@pytest.mark.asyncio
async def test_items_sorted_by_created_at_descending() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(
        user_id, count=3, day_offsets=[0, 5, 2]
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    result = await uc.execute(GetActivityHistoryQuery(user_profile_id=user_id))

    dates = [item.occurred_at for item in result.items]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.asyncio
async def test_total_reflects_all_matches_not_just_page() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(user_id, count=10)
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    result = await uc.execute(GetActivityHistoryQuery(user_profile_id=user_id, limit=3))

    assert result.total == 10
    assert len(result.items) == 3


@pytest.mark.asyncio
async def test_pagination_offset_slices_correctly() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(user_id, count=5, day_offsets=list(range(5)))
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    first_page = await uc.execute(GetActivityHistoryQuery(user_profile_id=user_id, limit=3, offset=0))
    second_page = await uc.execute(GetActivityHistoryQuery(user_profile_id=user_id, limit=3, offset=3))

    assert len(first_page.items) == 3
    assert len(second_page.items) == 2
    assert first_page.items[0].mission_match_id != second_page.items[0].mission_match_id


@pytest.mark.asyncio
async def test_empty_when_no_matches() -> None:
    user_id = uuid4()
    uc = _make_use_case(
        FakeMissionMatchRepository([]),
        FakeAnalyzedPostRepository([]),
        FakeRawPostRepository([]),
    )

    result = await uc.execute(GetActivityHistoryQuery(user_profile_id=user_id))

    assert result.items == []
    assert result.total == 0


@pytest.mark.asyncio
async def test_page_metadata_is_echoed_back() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(user_id, count=5)
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo)

    result = await uc.execute(GetActivityHistoryQuery(user_profile_id=user_id, limit=2, offset=1))

    assert result.limit == 2
    assert result.offset == 1


@pytest.mark.asyncio
async def test_user_isolation_only_own_matches_returned() -> None:
    user_a = uuid4()
    user_b = uuid4()
    raw_a = _make_raw_post()
    analyzed_a = _make_analyzed_post(raw_a.id)
    match_a = _make_match(user_a, analyzed_a.id)
    raw_b = _make_raw_post()
    analyzed_b = _make_analyzed_post(raw_b.id)
    match_b = _make_match(user_b, analyzed_b.id)

    uc = _make_use_case(
        FakeMissionMatchRepository([match_a, match_b]),
        FakeAnalyzedPostRepository([analyzed_a, analyzed_b]),
        FakeRawPostRepository([raw_a, raw_b]),
    )

    result = await uc.execute(GetActivityHistoryQuery(user_profile_id=user_a))

    assert result.total == 1
    assert result.items[0].mission_match_id == match_a.id
