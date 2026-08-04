"""Unit tests for SendDigestNow use case — no I/O, no real mailer/renderer/DB."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.Exception.application_error import UserProfileNotFoundError
from src.Application.Gateway.email_template_renderer_gateway import EmailTemplateRendererGateway
from src.Application.Gateway.mailer_gateway import MailerGateway
from src.Application.UseCase.digest_assembler import DigestAssembler
from src.Application.UseCase.send_digest_now import SendDigestNow
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.digest_email import DigestEmail
from src.Domain.Entity.digest_history import DigestHistory, DigestStatus
from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.digest_history_repository import DigestHistoryRepository
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


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeUserProfileRepository(UserProfileRepository):
    def __init__(self, profile: Optional[UserProfile] = None) -> None:
        self._profile = profile

    async def save(self, profile: UserProfile) -> None: ...
    async def get_by_email(self, email: str) -> Optional[UserProfile]: return None
    async def get_active_profile(self) -> Optional[UserProfile]: return self._profile
    async def delete(self, profile_id: UUID) -> None: ...

    async def get_by_id(self, profile_id: UUID) -> Optional[UserProfile]:
        if self._profile and self._profile.id == profile_id:
            return self._profile
        return None


class FakeMissionMatchRepository(MissionMatchRepository):
    def __init__(self, matches: Optional[list[MissionMatch]] = None) -> None:
        self._matches = matches or []

    async def save(self, match: MissionMatch) -> None: ...
    async def save_many(self, matches: list[MissionMatch]) -> None: ...
    async def get_by_id(self, match_id: UUID) -> Optional[MissionMatch]: return None
    async def get_by_user(self, user_id: UUID) -> list[MissionMatch]: return list(self._matches)
    async def get_by_post(self, post_id: UUID) -> list[MissionMatch]: return []
    async def get_best_matches(self, user_id: UUID, limit: int) -> list[MissionMatch]: return []
    async def delete_user_matches(self, user_id: UUID) -> None: ...


class FakeAnalyzedPostRepository(AnalyzedPostRepository):
    def __init__(self, posts: Optional[list[AnalyzedPost]] = None) -> None:
        self._posts = posts or []

    async def save(self, analyzed_post: AnalyzedPost) -> None: ...
    async def get_by_id(self, post_id: UUID) -> Optional[AnalyzedPost]: return None
    async def get_by_raw_post_id(self, raw_post_id: UUID) -> Optional[AnalyzedPost]: return None
    async def list_today_missions(self) -> list[AnalyzedPost]: return list(self._posts)
    async def list_missions(self, limit: int) -> list[AnalyzedPost]: return list(self._posts[:limit])
    async def find_by_raw_post_ids(self, raw_post_ids: list[UUID]) -> list[AnalyzedPost]: return []

    async def find_by_ids(self, ids: list[UUID]) -> list[AnalyzedPost]:
        return [p for p in self._posts if p.id in ids]


class FakeRawPostRepository(RawPostRepository):
    def __init__(self, posts: Optional[dict] = None) -> None:
        self._posts = posts or {}

    async def save(self, raw_post: object) -> None: ...
    async def exists_by_external_id(self, source: str, external_id: str) -> bool: return False
    async def get_by_id(self, raw_post_id: UUID) -> Optional[object]: return self._posts.get(raw_post_id)
    async def save_many(self, posts: list[object]) -> None: ...
    async def get_by_source_and_external_id(self, source: str, external_id: str) -> Optional[object]: return None
    async def list_recent(self, limit: int) -> list[object]: return []

    async def find_by_ids(self, ids: list[UUID]) -> list[object]:
        return [self._posts[i] for i in ids if i in self._posts]


class FakeSentMissionRepository(SentMissionRepository):
    def __init__(self) -> None:
        self.save_many_calls: list[tuple[UUID, list[UUID], datetime]] = []

    async def find_sent_analyzed_post_ids(self, user_id: UUID) -> set[UUID]:
        return set()

    async def save_many(self, user_id: UUID, analyzed_post_ids: list[UUID], sent_at: datetime) -> None:
        self.save_many_calls.append((user_id, list(analyzed_post_ids), sent_at))


class _FakeRawPost:
    def __init__(self, raw_post_id: UUID, post_url: str = "https://linkedin.com/post/123") -> None:
        self.id = raw_post_id
        self.post_url = post_url


class FakeRenderer(EmailTemplateRendererGateway):
    def __init__(self, html: str = "<html>digest</html>") -> None:
        self._html = html

    async def render(self, digest: DigestEmail) -> str:
        return self._html


class FailingRenderer(EmailTemplateRendererGateway):
    async def render(self, digest: DigestEmail) -> str:
        raise RuntimeError("template error")


class FakeMailer(MailerGateway):
    def __init__(self, message_id: Optional[str] = "provider-msg-1") -> None:
        self._message_id = message_id
        self.sent: list[dict] = []

    async def send(self, to: str, subject: str, html: str) -> Optional[str]:
        self.sent.append({"to": to, "subject": subject, "html": html})
        return self._message_id


class FailingMailer(MailerGateway):
    async def send(self, to: str, subject: str, html: str) -> Optional[str]:
        raise RuntimeError("mailer unavailable")


class FakeDigestHistoryRepository(DigestHistoryRepository):
    def __init__(self) -> None:
        self.saved: list[DigestHistory] = []

    async def save(self, history: DigestHistory) -> None:
        self.saved.append(history)

    async def find_by_user(self, user_id: UUID) -> list[DigestHistory]:
        return [h for h in self.saved if h.user_id == user_id]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: UUID) -> UserProfile:
    return UserProfile(
        id=user_id,
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


def _make_analyzed() -> AnalyzedPost:
    return AnalyzedPost(
        raw_post_id=uuid4(),
        summary="Mission Python full remote 700€/j.",
        title="Senior Python Engineer",
        company="Acme Corp",
        detected_stack=("python", "fastapi"),
        detected_remote_mode=RemoteMode.FULL_REMOTE,
        detected_tjm=700.0,
    )


def _make_match(analyzed_post_id: UUID, score: float = 0.85) -> MissionMatch:
    return MissionMatch.create(
        user_profile_id=uuid4(),
        analyzed_post_id=analyzed_post_id,
        match_score=MatchScore(semantic_score=score, contract_score=score, remote_score=score, tjm_score=score),
    )


def _make_assembler(
    user: Optional[UserProfile] = None,
    matches: Optional[list[MissionMatch]] = None,
    analyzed_posts: Optional[list[AnalyzedPost]] = None,
    raw_posts: Optional[dict] = None,
    sent_mission_repository: Optional[SentMissionRepository] = None,
) -> DigestAssembler:
    return DigestAssembler(
        user_profile_repository=FakeUserProfileRepository(user),
        mission_match_repository=FakeMissionMatchRepository(matches),
        analyzed_post_repository=FakeAnalyzedPostRepository(analyzed_posts),
        raw_post_repository=FakeRawPostRepository(raw_posts),
        selector=DigestMissionSelector(),
        generator=DigestGenerator(),
        sent_mission_repository=sent_mission_repository or FakeSentMissionRepository(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sends_digest_and_records_sent_history() -> None:
    user_id = uuid4()
    user = _make_user(user_id)
    analyzed = _make_analyzed()
    raw = _FakeRawPost(analyzed.raw_post_id)
    match = _make_match(analyzed.id)

    assembler = _make_assembler(user=user, matches=[match], analyzed_posts=[analyzed], raw_posts={raw.id: raw})
    mailer = FakeMailer(message_id="msg-123")
    history_repo = FakeDigestHistoryRepository()
    uc = SendDigestNow(
        digest_assembler=assembler,
        renderer=FakeRenderer(),
        mailer=mailer,
        digest_history_repository=history_repo,
        sent_mission_repository=FakeSentMissionRepository(),
    )

    result = await uc.execute(user_id)

    assert result.status == "sent"
    assert result.missions_count == 1
    assert result.provider_message_id == "msg-123"
    assert result.error_message is None
    assert mailer.sent[0]["to"] == "jean@example.com"

    assert len(history_repo.saved) == 1
    saved = history_repo.saved[0]
    assert saved.pipeline_run_id is None
    assert saved.status == DigestStatus.SENT
    assert saved.missions_count == 1
    assert saved.provider_message_id == "msg-123"


@pytest.mark.asyncio
async def test_mailer_failure_records_failed_history() -> None:
    user_id = uuid4()
    user = _make_user(user_id)
    analyzed = _make_analyzed()
    raw = _FakeRawPost(analyzed.raw_post_id)
    match = _make_match(analyzed.id)

    assembler = _make_assembler(user=user, matches=[match], analyzed_posts=[analyzed], raw_posts={raw.id: raw})
    history_repo = FakeDigestHistoryRepository()
    uc = SendDigestNow(
        digest_assembler=assembler,
        renderer=FakeRenderer(),
        mailer=FailingMailer(),
        digest_history_repository=history_repo,
        sent_mission_repository=FakeSentMissionRepository(),
    )

    result = await uc.execute(user_id)

    assert result.status == "failed"
    assert result.missions_count == 0
    assert result.provider_message_id is None
    assert "mailer unavailable" in result.error_message

    assert len(history_repo.saved) == 1
    saved = history_repo.saved[0]
    assert saved.status == DigestStatus.FAILED
    assert saved.pipeline_run_id is None


@pytest.mark.asyncio
async def test_renderer_failure_records_failed_history() -> None:
    user_id = uuid4()
    user = _make_user(user_id)
    assembler = _make_assembler(user=user, matches=[])
    history_repo = FakeDigestHistoryRepository()
    uc = SendDigestNow(
        digest_assembler=assembler,
        renderer=FailingRenderer(),
        mailer=FakeMailer(),
        digest_history_repository=history_repo,
        sent_mission_repository=FakeSentMissionRepository(),
    )

    result = await uc.execute(user_id)

    assert result.status == "failed"
    assert "template error" in result.error_message
    assert len(history_repo.saved) == 1


@pytest.mark.asyncio
async def test_user_not_found_propagates_and_records_no_history() -> None:
    assembler = _make_assembler(user=None)
    history_repo = FakeDigestHistoryRepository()
    uc = SendDigestNow(
        digest_assembler=assembler,
        renderer=FakeRenderer(),
        mailer=FakeMailer(),
        digest_history_repository=history_repo,
        sent_mission_repository=FakeSentMissionRepository(),
    )

    with pytest.raises(UserProfileNotFoundError):
        await uc.execute(uuid4())

    assert len(history_repo.saved) == 0


@pytest.mark.asyncio
async def test_empty_digest_is_still_sent() -> None:
    user_id = uuid4()
    user = _make_user(user_id)
    assembler = _make_assembler(user=user, matches=[])
    history_repo = FakeDigestHistoryRepository()
    uc = SendDigestNow(
        digest_assembler=assembler,
        renderer=FakeRenderer(),
        mailer=FakeMailer(),
        digest_history_repository=history_repo,
        sent_mission_repository=FakeSentMissionRepository(),
    )

    result = await uc.execute(user_id)

    assert result.status == "sent"
    assert result.missions_count == 0


# ---------------------------------------------------------------------------
# Persistance des missions envoyées (déduplication des prochains digests)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sent_missions_persisted_after_successful_send() -> None:
    user_id = uuid4()
    user = _make_user(user_id)
    analyzed = _make_analyzed()
    raw = _FakeRawPost(analyzed.raw_post_id)
    match = _make_match(analyzed.id)
    sent_repo = FakeSentMissionRepository()

    assembler = _make_assembler(
        user=user, matches=[match], analyzed_posts=[analyzed], raw_posts={raw.id: raw}, sent_mission_repository=sent_repo
    )
    uc = SendDigestNow(
        digest_assembler=assembler,
        renderer=FakeRenderer(),
        mailer=FakeMailer(),
        digest_history_repository=FakeDigestHistoryRepository(),
        sent_mission_repository=sent_repo,
    )

    await uc.execute(user_id)

    assert len(sent_repo.save_many_calls) == 1
    saved_user_id, saved_ids, _ = sent_repo.save_many_calls[0]
    assert saved_user_id == user_id
    assert saved_ids == [analyzed.id]


@pytest.mark.asyncio
async def test_sent_missions_not_persisted_when_mailer_fails() -> None:
    user_id = uuid4()
    user = _make_user(user_id)
    analyzed = _make_analyzed()
    raw = _FakeRawPost(analyzed.raw_post_id)
    match = _make_match(analyzed.id)
    sent_repo = FakeSentMissionRepository()

    assembler = _make_assembler(
        user=user, matches=[match], analyzed_posts=[analyzed], raw_posts={raw.id: raw}, sent_mission_repository=sent_repo
    )
    uc = SendDigestNow(
        digest_assembler=assembler,
        renderer=FakeRenderer(),
        mailer=FailingMailer(),
        digest_history_repository=FakeDigestHistoryRepository(),
        sent_mission_repository=sent_repo,
    )

    await uc.execute(user_id)

    assert sent_repo.save_many_calls == []


@pytest.mark.asyncio
async def test_sent_missions_not_persisted_when_renderer_fails() -> None:
    user_id = uuid4()
    user = _make_user(user_id)
    analyzed = _make_analyzed()
    raw = _FakeRawPost(analyzed.raw_post_id)
    match = _make_match(analyzed.id)
    sent_repo = FakeSentMissionRepository()

    assembler = _make_assembler(
        user=user, matches=[match], analyzed_posts=[analyzed], raw_posts={raw.id: raw}, sent_mission_repository=sent_repo
    )
    uc = SendDigestNow(
        digest_assembler=assembler,
        renderer=FailingRenderer(),
        mailer=FakeMailer(),
        digest_history_repository=FakeDigestHistoryRepository(),
        sent_mission_repository=sent_repo,
    )

    await uc.execute(user_id)

    assert sent_repo.save_many_calls == []


@pytest.mark.asyncio
async def test_sent_missions_not_persisted_when_digest_is_empty() -> None:
    user_id = uuid4()
    user = _make_user(user_id)
    sent_repo = FakeSentMissionRepository()

    assembler = _make_assembler(user=user, matches=[], sent_mission_repository=sent_repo)
    uc = SendDigestNow(
        digest_assembler=assembler,
        renderer=FakeRenderer(),
        mailer=FakeMailer(),
        digest_history_repository=FakeDigestHistoryRepository(),
        sent_mission_repository=sent_repo,
    )

    result = await uc.execute(user_id)

    assert result.status == "sent"
    assert sent_repo.save_many_calls == []
