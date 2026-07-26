"""Unit tests for ExplainMissionMatchTool — no I/O, no DB, no real MCP server. Fakes only."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.UseCase.get_mission_details import GetMissionDetails
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.Entity.raw_post import RawPost
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Exception.domain_exceptions import MissionMatchNotFoundError
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.raw_post_repository import RawPostRepository
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.match_score import MatchScore
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver
from src.Infrastructure.Mcp.Tool.explain_mission_match_tool import ExplainMissionMatchTool

_NOW = datetime.now(timezone.utc)


class FakeMissionMatchRepository(MissionMatchRepository):
    def __init__(self, matches: Optional[list[MissionMatch]] = None) -> None:
        self._matches = {m.id: m for m in (matches or [])}

    async def save(self, match: MissionMatch) -> None: ...
    async def save_many(self, matches: list[MissionMatch]) -> None: ...
    async def get_by_id(self, match_id: UUID) -> Optional[MissionMatch]:
        return self._matches.get(match_id)
    async def get_by_user(self, user_id: UUID) -> list[MissionMatch]: return []
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


class FakeUserProfileRepository(UserProfileRepository):
    def __init__(self, profile: Optional[UserProfile] = None) -> None:
        self._profile = profile

    async def save(self, profile: UserProfile) -> None: ...
    async def get_by_id(self, profile_id: UUID) -> Optional[UserProfile]:
        if self._profile and self._profile.id == profile_id:
            return self._profile
        return None
    async def get_by_email(self, email: str) -> Optional[UserProfile]: return None
    async def get_active_profile(self) -> Optional[UserProfile]: return self._profile
    async def delete(self, profile_id: UUID) -> None: ...


class FakeIdentityResolver(IdentityResolver):
    def __init__(self, user_profile_id: UUID) -> None:
        self._user_profile_id = user_profile_id

    async def resolve(self) -> UUID:
        return self._user_profile_id


def _make_user_profile(user_id: UUID, skills: list[str]) -> UserProfile:
    return UserProfile(
        id=user_id,
        email="freelancer@example.com",
        full_name="Jean Dupont",
        title="Senior Python Engineer",
        years_experience=10,
        preferred_contract_type=ContractType.FREELANCE,
        target_tjm=700.0,
        preferred_remote_mode=RemoteMode.FULL_REMOTE,
        skills=Stack.from_list(skills),
        availability=_NOW,
        location="Paris",
    )


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
        summary="Mission Python full remote 700€/j.",
        detected_stack=("fastapi", "python", "kubernetes"),
        detected_contract_type=ContractType.FREELANCE,
        detected_remote_mode=RemoteMode.FULL_REMOTE,
        detected_tjm=700.0,
        title="Senior Python Engineer",
        company="Acme Corp",
    )


def _build_scenario(user_id: UUID) -> tuple[
    FakeMissionMatchRepository, FakeAnalyzedPostRepository, FakeRawPostRepository, FakeUserProfileRepository, MissionMatch
]:
    user = _make_user_profile(user_id, ["python", "fastapi", "docker"])
    raw = _make_raw_post()
    analyzed = _make_analyzed_post(raw.id)
    match = MissionMatch.create(
        user_profile_id=user_id,
        analyzed_post_id=analyzed.id,
        match_score=MatchScore(semantic_score=0.8, contract_score=0.9, remote_score=1.0, tjm_score=0.7),
    )
    return (
        FakeMissionMatchRepository([match]),
        FakeAnalyzedPostRepository([analyzed]),
        FakeRawPostRepository([raw]),
        FakeUserProfileRepository(user),
        match,
    )


def _make_tool(
    identity_resolver: FakeIdentityResolver,
    match_repo: FakeMissionMatchRepository,
    analyzed_repo: FakeAnalyzedPostRepository,
    raw_repo: FakeRawPostRepository,
    user_repo: FakeUserProfileRepository,
) -> ExplainMissionMatchTool:
    get_mission_details = GetMissionDetails(match_repo, analyzed_repo, raw_repo, user_repo)
    return ExplainMissionMatchTool(identity_resolver=identity_resolver, get_mission_details=get_mission_details)


@pytest.mark.asyncio
async def test_explain_mission_match_returns_structured_explanation() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, user_repo, match = _build_scenario(user_id)
    tool = _make_tool(FakeIdentityResolver(user_id), match_repo, analyzed_repo, raw_repo, user_repo)

    payload = await tool.execute(match.id)

    assert payload["mission_match_id"] == str(match.id)
    assert payload["title"] == "Senior Python Engineer"
    assert payload["company"] == "Acme Corp"
    assert set(payload["score_details"].keys()) == {"semantic", "contract", "tjm", "remote"}
    assert set(payload["matched_skills"]) == {"python", "fastapi"}
    assert "kubernetes" in payload["missing_skills"]
    assert len(payload["matching_reasons"]) > 0


@pytest.mark.asyncio
async def test_explain_mission_match_does_not_leak_post_content() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, user_repo, match = _build_scenario(user_id)
    tool = _make_tool(FakeIdentityResolver(user_id), match_repo, analyzed_repo, raw_repo, user_repo)

    payload = await tool.execute(match.id)

    assert "content" not in payload
    assert "author_url" not in payload


@pytest.mark.asyncio
async def test_explain_mission_match_raises_for_mission_owned_by_another_user() -> None:
    user_id = uuid4()
    other_user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, _, match = _build_scenario(user_id)
    other_user = _make_user_profile(other_user_id, ["python"])
    tool = _make_tool(
        FakeIdentityResolver(other_user_id),
        match_repo,
        analyzed_repo,
        raw_repo,
        FakeUserProfileRepository(other_user),
    )

    with pytest.raises(MissionMatchNotFoundError):
        await tool.execute(match.id)


@pytest.mark.asyncio
async def test_explain_mission_match_raises_when_mission_not_found() -> None:
    user_id = uuid4()
    user = _make_user_profile(user_id, ["python"])
    tool = _make_tool(
        FakeIdentityResolver(user_id),
        FakeMissionMatchRepository([]),
        FakeAnalyzedPostRepository([]),
        FakeRawPostRepository([]),
        FakeUserProfileRepository(user),
    )

    with pytest.raises(MissionMatchNotFoundError):
        await tool.execute(uuid4())
