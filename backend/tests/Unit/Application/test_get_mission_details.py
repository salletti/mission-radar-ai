"""Unit tests for GetMissionDetails use case — no I/O, no DB, no external services."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.DTO.explainability_report import ExplainabilityReport
from src.Application.DTO.get_mission_details_query import GetMissionDetailsQuery
from src.Application.DTO.mission_match_detail import MissionMatchDetail
from src.Application.Exception.application_error import UserProfileNotFoundError
from src.Application.UseCase.get_mission_details import GetMissionDetails
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.mission_match import MissionMatch as MissionMatchEntity
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

_NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Fake implementations
# ---------------------------------------------------------------------------


class FakeMissionMatchRepository(MissionMatchRepository):
    def __init__(self, matches: Optional[list[MissionMatchEntity]] = None) -> None:
        self._matches = {m.id: m for m in (matches or [])}

    async def save(self, match: MissionMatchEntity) -> None:
        self._matches[match.id] = match

    async def save_many(self, matches: list[MissionMatchEntity]) -> None:
        for m in matches:
            self._matches[m.id] = m

    async def get_by_id(self, match_id: UUID) -> Optional[MissionMatchEntity]:
        return self._matches.get(match_id)

    async def get_by_user(self, user_id: UUID) -> list[MissionMatchEntity]:
        return [m for m in self._matches.values() if m.user_profile_id == user_id]

    async def get_by_post(self, post_id: UUID) -> list[MissionMatchEntity]:
        return [m for m in self._matches.values() if m.analyzed_post_id == post_id]

    async def get_best_matches(self, user_id: UUID, limit: int) -> list[MissionMatchEntity]:
        return sorted(
            [m for m in self._matches.values() if m.user_profile_id == user_id],
            key=lambda m: m.final_score,
            reverse=True,
        )[:limit]

    async def delete_user_matches(self, user_id: UUID) -> None:
        self._matches = {k: v for k, v in self._matches.items() if v.user_profile_id != user_id}


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


class FakeUserProfileRepository(UserProfileRepository):
    def __init__(self, profile: Optional[UserProfile] = None) -> None:
        self._profile = profile

    async def save(self, profile: UserProfile) -> None:
        self._profile = profile

    async def get_by_id(self, profile_id: UUID) -> Optional[UserProfile]:
        if self._profile and self._profile.id == profile_id:
            return self._profile
        return None

    async def get_by_email(self, email: str) -> Optional[UserProfile]:
        if self._profile and self._profile.email == email:
            return self._profile
        return None

    async def get_active_profile(self) -> Optional[UserProfile]:
        return self._profile

    async def delete(self, profile_id: UUID) -> None:
        if self._profile and self._profile.id == profile_id:
            self._profile = None


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


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
        location="Paris",
    )


def _make_match(user_profile_id: UUID, analyzed_post_id: UUID) -> MissionMatchEntity:
    return MissionMatchEntity.create(
        user_profile_id=user_profile_id,
        analyzed_post_id=analyzed_post_id,
        match_score=MatchScore(
            semantic_score=0.8,
            contract_score=0.9,
            remote_score=1.0,
            tjm_score=0.7,
        ),
    )


def _build_scenario(
    user_id: UUID,
    user_skills: list[str] | None = None,
) -> tuple[
    FakeMissionMatchRepository,
    FakeAnalyzedPostRepository,
    FakeRawPostRepository,
    FakeUserProfileRepository,
    MissionMatchEntity,
]:
    skills = user_skills or ["python", "fastapi", "docker"]
    user = _make_user_profile(user_id, skills)
    raw = _make_raw_post()
    analyzed = _make_analyzed_post(raw.id)
    match = _make_match(user_id, analyzed.id)
    return (
        FakeMissionMatchRepository([match]),
        FakeAnalyzedPostRepository([analyzed]),
        FakeRawPostRepository([raw]),
        FakeUserProfileRepository(user),
        match,
    )


def _make_use_case(
    match_repo: FakeMissionMatchRepository,
    analyzed_repo: FakeAnalyzedPostRepository,
    raw_repo: FakeRawPostRepository,
    user_repo: FakeUserProfileRepository,
) -> GetMissionDetails:
    return GetMissionDetails(match_repo, analyzed_repo, raw_repo, user_repo)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_get_mission_details_returns_full_detail() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, user_repo, match = _build_scenario(user_id)
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo, user_repo)

    result = await uc.execute(GetMissionDetailsQuery(
        mission_match_id=match.id,
        user_profile_id=user_id,
    ))

    assert isinstance(result, MissionMatchDetail)
    assert result.mission_match_id == match.id
    assert result.title == "Senior Python Engineer"
    assert result.company == "Acme Corp"
    assert result.location == "Paris"
    assert result.summary == "Mission Python full remote 700€/j."
    assert result.author_url == "https://linkedin.com/in/alice"
    assert result.detected_tjm == 700.0
    assert result.global_score == match.final_score
    assert result.matched_at == match.created_at


async def test_get_mission_details_score_details_has_four_keys() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, user_repo, match = _build_scenario(user_id)
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo, user_repo)

    result = await uc.execute(GetMissionDetailsQuery(
        mission_match_id=match.id,
        user_profile_id=user_id,
    ))

    assert set(result.score_details.keys()) == {"semantic", "contract", "tjm", "remote"}


async def test_get_mission_details_content_not_truncated() -> None:
    user_id = uuid4()
    long_content = "x" * 1000
    raw = RawPost(
        source="linkedin",
        external_id=str(uuid4()),
        author_name="Bob",
        author_url="https://linkedin.com/in/bob",
        content=long_content,
        post_url="https://linkedin.com/posts/1",
        published_at=_NOW,
        scraped_at=_NOW,
    )
    analyzed = _make_analyzed_post(raw.id)
    match = _make_match(user_id, analyzed.id)
    user = _make_user_profile(user_id, ["python"])
    uc = _make_use_case(
        FakeMissionMatchRepository([match]),
        FakeAnalyzedPostRepository([analyzed]),
        FakeRawPostRepository([raw]),
        FakeUserProfileRepository(user),
    )

    result = await uc.execute(GetMissionDetailsQuery(
        mission_match_id=match.id,
        user_profile_id=user_id,
    ))

    assert len(result.content) == 1000


async def test_get_mission_details_raises_when_not_found() -> None:
    user_id = uuid4()
    user = _make_user_profile(user_id, ["python"])
    uc = _make_use_case(
        FakeMissionMatchRepository([]),
        FakeAnalyzedPostRepository([]),
        FakeRawPostRepository([]),
        FakeUserProfileRepository(user),
    )

    with pytest.raises(MissionMatchNotFoundError):
        await uc.execute(GetMissionDetailsQuery(
            mission_match_id=uuid4(),
            user_profile_id=user_id,
        ))


async def test_get_mission_details_raises_when_wrong_user() -> None:
    user_id = uuid4()
    other_user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, user_repo, match = _build_scenario(user_id)
    other_user = _make_user_profile(other_user_id, ["python"])
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo, FakeUserProfileRepository(other_user))

    with pytest.raises(MissionMatchNotFoundError):
        await uc.execute(GetMissionDetailsQuery(
            mission_match_id=match.id,
            user_profile_id=other_user_id,
        ))


async def test_get_mission_details_raises_when_analyzed_post_missing() -> None:
    user_id = uuid4()
    analyzed_post_id = uuid4()
    match = _make_match(user_id, analyzed_post_id)
    user = _make_user_profile(user_id, ["python"])
    uc = _make_use_case(
        FakeMissionMatchRepository([match]),
        FakeAnalyzedPostRepository([]),
        FakeRawPostRepository([]),
        FakeUserProfileRepository(user),
    )

    with pytest.raises(MissionMatchNotFoundError):
        await uc.execute(GetMissionDetailsQuery(
            mission_match_id=match.id,
            user_profile_id=user_id,
        ))


async def test_matched_skills_are_intersection_of_user_and_mission() -> None:
    user_id = uuid4()
    # user has python + fastapi + docker; mission has fastapi + python + kubernetes
    match_repo, analyzed_repo, raw_repo, user_repo, match = _build_scenario(
        user_id, user_skills=["python", "fastapi", "docker"]
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo, user_repo)

    result = await uc.execute(GetMissionDetailsQuery(
        mission_match_id=match.id,
        user_profile_id=user_id,
    ))

    assert set(result.matched_skills) == {"python", "fastapi"}


async def test_missing_skills_are_in_mission_but_not_user() -> None:
    user_id = uuid4()
    # mission has fastapi + python + kubernetes; user lacks kubernetes
    match_repo, analyzed_repo, raw_repo, user_repo, match = _build_scenario(
        user_id, user_skills=["python", "fastapi", "docker"]
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo, user_repo)

    result = await uc.execute(GetMissionDetailsQuery(
        mission_match_id=match.id,
        user_profile_id=user_id,
    ))

    assert "kubernetes" in result.missing_skills
    assert "python" not in result.missing_skills


async def test_explanation_matching_reasons_not_empty_with_good_match() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, user_repo, match = _build_scenario(
        user_id, user_skills=["python", "fastapi", "docker"]
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo, user_repo)

    result = await uc.execute(GetMissionDetailsQuery(
        mission_match_id=match.id,
        user_profile_id=user_id,
    ))

    assert isinstance(result.explanation, ExplainabilityReport)
    assert len(result.explanation.matching_reasons) > 0


async def test_explanation_matching_reasons_are_strings() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, user_repo, match = _build_scenario(user_id)
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo, user_repo)

    result = await uc.execute(GetMissionDetailsQuery(
        mission_match_id=match.id,
        user_profile_id=user_id,
    ))

    assert all(isinstance(r, str) for r in result.explanation.matching_reasons)


async def test_score_breakdown_contract_and_daily_rate_are_populated() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, user_repo, match = _build_scenario(user_id)
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo, user_repo)

    result = await uc.execute(GetMissionDetailsQuery(
        mission_match_id=match.id,
        user_profile_id=user_id,
    ))

    breakdown = result.explanation.score_breakdown
    assert breakdown.contract is not None
    assert breakdown.daily_rate is not None
    assert breakdown.contract == match.match_score.contract_score
    assert breakdown.daily_rate == match.match_score.tjm_score


async def test_score_breakdown_skills_experience_location_are_none() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, user_repo, match = _build_scenario(user_id)
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo, user_repo)

    result = await uc.execute(GetMissionDetailsQuery(
        mission_match_id=match.id,
        user_profile_id=user_id,
    ))

    breakdown = result.explanation.score_breakdown
    assert breakdown.skills is None
    assert breakdown.experience is None
    assert breakdown.location is None


async def test_explanation_strong_points_match_matched_skills() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, user_repo, match = _build_scenario(
        user_id, user_skills=["python", "fastapi", "docker"]
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo, user_repo)

    result = await uc.execute(GetMissionDetailsQuery(
        mission_match_id=match.id,
        user_profile_id=user_id,
    ))

    assert set(result.explanation.strong_points) == set(result.matched_skills)


async def test_explanation_missing_skills_mirrors_top_level() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, user_repo, match = _build_scenario(
        user_id, user_skills=["python", "fastapi", "docker"]
    )
    uc = _make_use_case(match_repo, analyzed_repo, raw_repo, user_repo)

    result = await uc.execute(GetMissionDetailsQuery(
        mission_match_id=match.id,
        user_profile_id=user_id,
    ))

    assert set(result.explanation.missing_skills) == set(result.missing_skills)


async def test_raises_when_user_profile_not_found() -> None:
    user_id = uuid4()
    match_repo, analyzed_repo, raw_repo, _, match = _build_scenario(user_id)
    uc = _make_use_case(
        match_repo, analyzed_repo, raw_repo, FakeUserProfileRepository(None)
    )

    with pytest.raises(UserProfileNotFoundError):
        await uc.execute(GetMissionDetailsQuery(
            mission_match_id=match.id,
            user_profile_id=user_id,
        ))
