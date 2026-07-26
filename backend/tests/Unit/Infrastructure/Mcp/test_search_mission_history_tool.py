"""Unit tests for SearchMissionHistoryTool — no I/O, no DB, no real MCP server. Fakes only."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.UseCase.search_mission_history import SearchMissionHistory
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.Entity.raw_post import RawPost
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.raw_post_repository import RawPostRepository
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.match_score import MatchScore
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver
from src.Infrastructure.Mcp.Tool.search_mission_history_tool import SearchMissionHistoryTool

_NOW = datetime.now(timezone.utc)


class FakeMissionMatchRepository(MissionMatchRepository):
    def __init__(self, matches: Optional[list[MissionMatch]] = None) -> None:
        self._matches = matches or []

    async def get_by_user(self, user_id: UUID) -> list[MissionMatch]:
        return [m for m in self._matches if m.user_profile_id == user_id]

    async def save(self, match: MissionMatch) -> None: ...
    async def save_many(self, matches: list[MissionMatch]) -> None: ...
    async def get_by_id(self, match_id: UUID) -> Optional[MissionMatch]: return None
    async def get_by_post(self, post_id: UUID) -> list[MissionMatch]: return []
    async def get_best_matches(self, user_id: UUID, limit: int) -> list[MissionMatch]: return []
    async def delete_user_matches(self, user_id: UUID) -> None: ...


class FakeAnalyzedPostRepository(AnalyzedPostRepository):
    def __init__(self, posts: Optional[list[AnalyzedPost]] = None) -> None:
        self._posts: dict[UUID, AnalyzedPost] = {p.id: p for p in (posts or [])}

    async def save(self, analyzed_post: AnalyzedPost) -> None: ...
    async def get_by_id(self, post_id: UUID) -> Optional[AnalyzedPost]: return self._posts.get(post_id)
    async def get_by_raw_post_id(self, raw_post_id: UUID) -> Optional[AnalyzedPost]: return None
    async def list_today_missions(self) -> list[AnalyzedPost]: return list(self._posts.values())
    async def list_missions(self, limit: int) -> list[AnalyzedPost]: return list(self._posts.values())[:limit]
    async def find_by_raw_post_ids(self, raw_post_ids: list[UUID]) -> list[AnalyzedPost]: return []
    async def find_by_ids(self, ids: list[UUID]) -> list[AnalyzedPost]:
        return [p for p in self._posts.values() if p.id in ids]


class FakeRawPostRepository(RawPostRepository):
    def __init__(self, posts: Optional[list[RawPost]] = None) -> None:
        self._posts: dict[UUID, RawPost] = {p.id: p for p in (posts or [])}

    async def save(self, raw_post: RawPost) -> None: ...
    async def exists_by_external_id(self, source: str, external_id: str) -> bool: return False
    async def get_by_id(self, raw_post_id: UUID) -> Optional[RawPost]: return self._posts.get(raw_post_id)
    async def save_many(self, posts: list[RawPost]) -> None: ...
    async def get_by_source_and_external_id(self, source: str, external_id: str) -> Optional[RawPost]: return None
    async def list_recent(self, limit: int) -> list[RawPost]: return list(self._posts.values())[:limit]
    async def find_by_ids(self, ids: list[UUID]) -> list[RawPost]:
        return [p for p in self._posts.values() if p.id in ids]


class FakeIdentityResolver(IdentityResolver):
    def __init__(self, user_profile_id: UUID) -> None:
        self._user_profile_id = user_profile_id

    async def resolve(self) -> UUID:
        return self._user_profile_id


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


def _make_analyzed_post(raw_post_id: UUID, title: str) -> AnalyzedPost:
    return AnalyzedPost(
        raw_post_id=raw_post_id,
        summary="Mission Python full remote.",
        detected_stack=("fastapi", "python"),
        detected_contract_type=ContractType.FREELANCE,
        detected_remote_mode=RemoteMode.FULL_REMOTE,
        detected_tjm=700.0,
        title=title,
    )


def _build_scenario(user_id: UUID, titles: list[str]) -> tuple[
    FakeMissionMatchRepository, FakeAnalyzedPostRepository, FakeRawPostRepository
]:
    raws, analyzed_list, matches = [], [], []
    for title in titles:
        raw = _make_raw_post()
        analyzed = _make_analyzed_post(raw.id, title)
        match = MissionMatch.create(
            user_profile_id=user_id,
            analyzed_post_id=analyzed.id,
            match_score=MatchScore(semantic_score=0.8, contract_score=0.8, remote_score=0.8, tjm_score=0.8),
        )
        raws.append(raw)
        analyzed_list.append(analyzed)
        matches.append(match)
    return (
        FakeMissionMatchRepository(matches),
        FakeAnalyzedPostRepository(analyzed_list),
        FakeRawPostRepository(raws),
    )


def _make_tool(
    user_id: UUID,
    match_repo: FakeMissionMatchRepository,
    analyzed_repo: FakeAnalyzedPostRepository,
    raw_repo: FakeRawPostRepository,
) -> SearchMissionHistoryTool:
    search_mission_history = SearchMissionHistory(match_repo, analyzed_repo, raw_repo)
    return SearchMissionHistoryTool(
        identity_resolver=FakeIdentityResolver(user_id), search_mission_history=search_mission_history
    )


@pytest.mark.asyncio
async def test_search_mission_history_tool_returns_matching_keyword() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(
        user_id, ["Senior Kubernetes Engineer", "Frontend Developer"]
    )
    tool = _make_tool(user_id, match_repo, analyzed_repo, raw_repo)

    payload = await tool.execute(keyword="kubernetes")

    assert len(payload["missions"]) == 1
    assert payload["missions"][0]["title"] == "Senior Kubernetes Engineer"


@pytest.mark.asyncio
async def test_search_mission_history_tool_returns_all_when_no_keyword() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(user_id, ["Mission A", "Mission B"])
    tool = _make_tool(user_id, match_repo, analyzed_repo, raw_repo)

    payload = await tool.execute()

    assert len(payload["missions"]) == 2


@pytest.mark.asyncio
async def test_search_mission_history_tool_returns_empty_list_when_no_match() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo = _build_scenario(user_id, ["Mission A"])
    tool = _make_tool(user_id, match_repo, analyzed_repo, raw_repo)

    payload = await tool.execute(keyword="rust")

    assert payload == {"missions": []}
