"""Unit tests for GenerateDigest use case — no I/O, no DB, no external services."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.Exception.application_error import UserProfileNotFoundError
from src.Application.UseCase.generate_digest import GenerateDigest
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.digest_email import DigestEmail
from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.raw_post_repository import RawPostRepository
from src.Domain.Repository.sent_mission_repository import SentMissionRepository
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Domain.Service.digest_generator import DigestGenerator
from src.Domain.Service.digest_mission_selector import DigestMissionSelector
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.match_score import MatchScore
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack

_AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)
_NOW = datetime(2026, 6, 30, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: UUID | None = None) -> UserProfile:
    return UserProfile(
        id=user_id or uuid4(),
        email="jean@example.com",
        full_name="Jean Dupont",
        title="Senior Python Engineer",
        years_experience=15,
        preferred_contract_type=ContractType.FREELANCE,
        target_tjm=700.0,
        preferred_remote_mode=RemoteMode.FULL_REMOTE,
        skills=Stack(("python", "fastapi")),
        availability=_AVAILABILITY,
    )


def _make_match(score: float = 0.85, analyzed_post_id: UUID | None = None) -> MissionMatch:
    match_score = MatchScore(
        semantic_score=score,
        contract_score=score,
        remote_score=score,
        tjm_score=score,
    )
    return MissionMatch.create(
        user_profile_id=uuid4(),
        analyzed_post_id=analyzed_post_id or uuid4(),
        match_score=match_score,
    )


def _make_analyzed(post_id: UUID | None = None, raw_post_id: UUID | None = None) -> AnalyzedPost:
    return AnalyzedPost(
        id=post_id or uuid4(),
        raw_post_id=raw_post_id or uuid4(),
        summary="Mission Symfony senior — full remote — 700€/j",
        title="Lead Symfony Developer",
        company="Acme Corp",
        detected_stack=("symfony", "php"),
        detected_remote_mode=RemoteMode.FULL_REMOTE,
        detected_tjm=700.0,
    )


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeUserProfileRepository(UserProfileRepository):
    def __init__(self, profile: UserProfile | None = None) -> None:
        self._profile = profile

    async def save(self, profile: UserProfile) -> None:
        self._profile = profile

    async def get_by_id(self, profile_id: UUID) -> Optional[UserProfile]:
        if self._profile and self._profile.id == profile_id:
            return self._profile
        return None

    async def get_by_email(self, email: str) -> Optional[UserProfile]:
        return None

    async def get_active_profile(self) -> Optional[UserProfile]:
        return self._profile

    async def delete(self, profile_id: UUID) -> None:
        pass


class FakeMissionMatchRepository(MissionMatchRepository):
    def __init__(self, matches: list[MissionMatch] | None = None) -> None:
        self._matches = matches or []

    async def save(self, match: MissionMatch) -> None:
        self._matches.append(match)

    async def save_many(self, matches: list[MissionMatch]) -> None:
        self._matches.extend(matches)

    async def get_by_id(self, match_id: UUID) -> Optional[MissionMatch]:
        return next((m for m in self._matches if m.id == match_id), None)

    async def get_by_user(self, user_id: UUID) -> list[MissionMatch]:
        return list(self._matches)

    async def get_by_post(self, post_id: UUID) -> list[MissionMatch]:
        return []

    async def get_best_matches(self, user_id: UUID, limit: int) -> list[MissionMatch]:
        return sorted(self._matches, key=lambda m: m.final_score, reverse=True)[:limit]

    async def delete_user_matches(self, user_id: UUID) -> None:
        self._matches.clear()


class FakeAnalyzedPostRepository(AnalyzedPostRepository):
    def __init__(self, posts: list[AnalyzedPost] | None = None) -> None:
        self._posts = posts or []

    async def save(self, analyzed_post: AnalyzedPost) -> None:
        self._posts.append(analyzed_post)

    async def get_by_id(self, post_id: UUID) -> Optional[AnalyzedPost]:
        return next((p for p in self._posts if p.id == post_id), None)

    async def get_by_raw_post_id(self, raw_post_id: UUID) -> Optional[AnalyzedPost]:
        return None

    async def list_today_missions(self) -> list[AnalyzedPost]:
        return list(self._posts)

    async def list_missions(self, limit: int) -> list[AnalyzedPost]:
        return list(self._posts[:limit])

    async def find_by_raw_post_ids(self, raw_post_ids: list[UUID]) -> list[AnalyzedPost]:
        return [p for p in self._posts if p.raw_post_id in raw_post_ids]

    async def find_by_ids(self, ids: list[UUID]) -> list[AnalyzedPost]:
        return [p for p in self._posts if p.id in ids]


class FakeRawPostRepository(RawPostRepository):
    def __init__(self, posts: dict[UUID, object] | None = None) -> None:
        self._posts: dict[UUID, object] = posts or {}

    async def save(self, raw_post: object) -> None:
        pass

    async def exists_by_external_id(self, source: str, external_id: str) -> bool:
        return False

    async def get_by_id(self, raw_post_id: UUID) -> Optional[object]:
        return self._posts.get(raw_post_id)

    async def save_many(self, posts: list[object]) -> None:
        pass

    async def get_by_source_and_external_id(self, source: str, external_id: str) -> Optional[object]:
        return None

    async def list_recent(self, limit: int) -> list[object]:
        return []

    async def find_by_ids(self, ids: list[UUID]) -> list[object]:
        return [self._posts[i] for i in ids if i in self._posts]


class FakeSentMissionRepository(SentMissionRepository):
    def __init__(self, sent: set[tuple[UUID, UUID]] | None = None) -> None:
        self._sent = sent or set()

    async def find_sent_analyzed_post_ids(self, user_id: UUID) -> set[UUID]:
        return {ap_id for (uid, ap_id) in self._sent if uid == user_id}

    async def save_many(self, user_id: UUID, analyzed_post_ids: list[UUID], sent_at: datetime) -> None:
        self._sent.update((user_id, ap_id) for ap_id in analyzed_post_ids)


class _FakeRawPost:
    """Minimal stub — only post_url is accessed by GenerateDigest."""

    def __init__(self, raw_post_id: UUID, post_url: str = "https://linkedin.com/post/123") -> None:
        self.id = raw_post_id
        self.post_url = post_url


def _make_use_case(
    user: UserProfile | None = None,
    matches: list[MissionMatch] | None = None,
    analyzed_posts: list[AnalyzedPost] | None = None,
    raw_posts: dict[UUID, _FakeRawPost] | None = None,
    sent: set[tuple[UUID, UUID]] | None = None,
) -> GenerateDigest:
    return GenerateDigest(
        user_profile_repository=FakeUserProfileRepository(user),
        mission_match_repository=FakeMissionMatchRepository(matches),
        analyzed_post_repository=FakeAnalyzedPostRepository(analyzed_posts),
        raw_post_repository=FakeRawPostRepository(raw_posts),  # type: ignore[arg-type]
        selector=DigestMissionSelector(),
        generator=DigestGenerator(),
        sent_mission_repository=FakeSentMissionRepository(sent),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_returns_digest_email_with_missions():
    user_id = uuid4()
    user = _make_user(user_id)
    analyzed = _make_analyzed()
    raw_post_id = analyzed.raw_post_id
    raw = _FakeRawPost(raw_post_id, "https://linkedin.com/post/abc")
    match = _make_match(score=0.9, analyzed_post_id=analyzed.id)

    uc = _make_use_case(
        user=user,
        matches=[match],
        analyzed_posts=[analyzed],
        raw_posts={raw_post_id: raw},
    )
    digest = await uc.execute(user_id)

    assert isinstance(digest, DigestEmail)
    assert digest.user_id == user_id
    assert digest.user_email == "jean@example.com"
    assert digest.user_name == "Jean Dupont"
    assert digest.mission_count == 1


async def test_digest_mission_fields_assembled_correctly():
    user_id = uuid4()
    user = _make_user(user_id)
    analyzed = _make_analyzed()
    raw_post_id = analyzed.raw_post_id
    raw = _FakeRawPost(raw_post_id, "https://linkedin.com/post/xyz")
    match = _make_match(score=0.85, analyzed_post_id=analyzed.id)

    uc = _make_use_case(
        user=user,
        matches=[match],
        analyzed_posts=[analyzed],
        raw_posts={raw_post_id: raw},
    )
    digest = await uc.execute(user_id)

    dm = digest.missions[0]
    assert dm.mission_match_id == match.id
    assert dm.analyzed_post_id == analyzed.id
    assert dm.final_score == pytest.approx(match.final_score, abs=0.01)
    assert dm.summary == analyzed.summary
    assert dm.title == analyzed.title
    assert dm.company == analyzed.company
    assert dm.detected_stack == analyzed.detected_stack
    assert dm.post_url == "https://linkedin.com/post/xyz"


async def test_post_url_is_none_when_raw_post_missing():
    user_id = uuid4()
    user = _make_user(user_id)
    analyzed = _make_analyzed()
    match = _make_match(analyzed_post_id=analyzed.id)

    uc = _make_use_case(
        user=user,
        matches=[match],
        analyzed_posts=[analyzed],
        raw_posts={},  # no raw post
    )
    digest = await uc.execute(user_id)

    assert digest.missions[0].post_url is None


async def test_user_not_found_raises_error():
    uc = _make_use_case(user=None)
    with pytest.raises(UserProfileNotFoundError):
        await uc.execute(uuid4())


async def test_no_matches_returns_empty_digest():
    user_id = uuid4()
    user = _make_user(user_id)

    uc = _make_use_case(user=user, matches=[])
    digest = await uc.execute(user_id)

    assert isinstance(digest, DigestEmail)
    assert digest.mission_count == 0
    assert "Aucune nouvelle mission" in digest.subject


async def test_top_n_selection_applied():
    """More than 10 matches → only top 10 in the digest."""
    user_id = uuid4()
    user = _make_user(user_id)

    analyzed_posts = [_make_analyzed() for _ in range(15)]
    raw_posts = {ap.raw_post_id: _FakeRawPost(ap.raw_post_id) for ap in analyzed_posts}
    matches = [
        _make_match(score=round(0.5 + i * 0.03, 2), analyzed_post_id=ap.id)
        for i, ap in enumerate(analyzed_posts)
    ]

    uc = _make_use_case(
        user=user,
        matches=matches,
        analyzed_posts=analyzed_posts,
        raw_posts=raw_posts,
    )
    digest = await uc.execute(user_id)

    assert digest.mission_count == 10


async def test_missions_sorted_by_score_descending():
    user_id = uuid4()
    user = _make_user(user_id)

    scores = [0.6, 0.9, 0.75]
    analyzed_posts = [_make_analyzed() for _ in scores]
    raw_posts = {ap.raw_post_id: _FakeRawPost(ap.raw_post_id) for ap in analyzed_posts}
    matches = [
        _make_match(score=s, analyzed_post_id=ap.id)
        for s, ap in zip(scores, analyzed_posts)
    ]

    uc = _make_use_case(
        user=user,
        matches=matches,
        analyzed_posts=analyzed_posts,
        raw_posts=raw_posts,
    )
    digest = await uc.execute(user_id)

    result_scores = [dm.final_score for dm in digest.missions]
    assert result_scores == sorted(result_scores, reverse=True)


async def test_subject_reflects_mission_count():
    user_id = uuid4()
    user = _make_user(user_id)
    analyzed = _make_analyzed()
    raw_post_id = analyzed.raw_post_id
    raw = _FakeRawPost(raw_post_id)
    match = _make_match(analyzed_post_id=analyzed.id)

    uc = _make_use_case(
        user=user,
        matches=[match],
        analyzed_posts=[analyzed],
        raw_posts={raw_post_id: raw},
    )
    digest = await uc.execute(user_id)

    assert "1" in digest.subject
    assert "mission" in digest.subject.lower()


# ---------------------------------------------------------------------------
# Exclusion des missions déjà envoyées
# ---------------------------------------------------------------------------


async def test_excludes_previously_sent_missions_from_digest():
    user_id = uuid4()
    user = _make_user(user_id)

    analyzed_a = _make_analyzed()
    analyzed_b = _make_analyzed()
    raw_posts = {
        analyzed_a.raw_post_id: _FakeRawPost(analyzed_a.raw_post_id),
        analyzed_b.raw_post_id: _FakeRawPost(analyzed_b.raw_post_id),
    }
    matches = [
        _make_match(score=0.9, analyzed_post_id=analyzed_a.id),
        _make_match(score=0.7, analyzed_post_id=analyzed_b.id),
    ]

    uc = _make_use_case(
        user=user,
        matches=matches,
        analyzed_posts=[analyzed_a, analyzed_b],
        raw_posts=raw_posts,
        sent={(user_id, analyzed_a.id)},
    )
    digest = await uc.execute(user_id)

    assert digest.mission_count == 1
    assert digest.missions[0].analyzed_post_id == analyzed_b.id


async def test_top_n_recomputed_after_exclusion():
    user_id = uuid4()
    user = _make_user(user_id)

    analyzed_posts = [_make_analyzed() for _ in range(12)]
    raw_posts = {ap.raw_post_id: _FakeRawPost(ap.raw_post_id) for ap in analyzed_posts}
    matches = [
        _make_match(score=round(0.9 - i * 0.05, 2), analyzed_post_id=ap.id)
        for i, ap in enumerate(analyzed_posts)
    ]
    # Exclut les 3 mieux scorées (les 3 premières, déjà envoyées lors d'un digest précédent)
    sent = {(user_id, ap.id) for ap in analyzed_posts[:3]}

    uc = _make_use_case(
        user=user,
        matches=matches,
        analyzed_posts=analyzed_posts,
        raw_posts=raw_posts,
        sent=sent,
    )
    digest = await uc.execute(user_id)

    excluded_ids = {ap.id for ap in analyzed_posts[:3]}
    assert digest.mission_count == 9
    assert all(dm.analyzed_post_id not in excluded_ids for dm in digest.missions)
    result_scores = [dm.final_score for dm in digest.missions]
    assert result_scores == sorted(result_scores, reverse=True)


async def test_no_regression_when_no_sent_missions():
    user_id = uuid4()
    user = _make_user(user_id)
    analyzed = _make_analyzed()
    raw_post_id = analyzed.raw_post_id
    raw = _FakeRawPost(raw_post_id)
    match = _make_match(score=0.9, analyzed_post_id=analyzed.id)

    uc = _make_use_case(
        user=user,
        matches=[match],
        analyzed_posts=[analyzed],
        raw_posts={raw_post_id: raw},
        sent=set(),
    )
    digest = await uc.execute(user_id)

    assert digest.mission_count == 1
