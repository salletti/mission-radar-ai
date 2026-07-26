"""Unit tests for SendDigestNowTool — no I/O, no DB, no real MCP server. Fakes only."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.Gateway.email_template_renderer_gateway import EmailTemplateRendererGateway
from src.Application.Gateway.mailer_gateway import MailerGateway
from src.Application.UseCase.digest_assembler import DigestAssembler
from src.Application.UseCase.send_digest_now import SendDigestNow
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.digest_email import DigestEmail
from src.Domain.Entity.digest_history import DigestHistory
from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.digest_history_repository import DigestHistoryRepository
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.raw_post_repository import RawPostRepository
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Domain.Service.digest_generator import DigestGenerator
from src.Domain.Service.digest_mission_selector import DigestMissionSelector
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver
from src.Infrastructure.Mcp.Tool.send_digest_now_tool import SendDigestNowTool

_AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)


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


class FakeRenderer(EmailTemplateRendererGateway):
    async def render(self, digest: DigestEmail) -> str:
        return "<html>digest</html>"


class FakeMailer(MailerGateway):
    async def send(self, to: str, subject: str, html: str) -> Optional[str]:
        return "msg-123"


class FakeDigestHistoryRepository(DigestHistoryRepository):
    def __init__(self) -> None:
        self.saved: list[DigestHistory] = []

    async def save(self, history: DigestHistory) -> None:
        self.saved.append(history)

    async def find_by_user(self, user_id: UUID) -> list[DigestHistory]:
        return [h for h in self.saved if h.user_id == user_id]


class FakeIdentityResolver(IdentityResolver):
    def __init__(self, user_profile_id: UUID) -> None:
        self._user_profile_id = user_profile_id

    async def resolve(self) -> UUID:
        return self._user_profile_id


def _make_user(user_id: UUID) -> UserProfile:
    return UserProfile(
        id=user_id,
        email="jean@example.com",
        full_name="Jean Dupont",
        title="Senior Python Engineer",
        years_experience=10,
        preferred_contract_type=ContractType.FREELANCE,
        target_tjm=700.0,
        preferred_remote_mode=RemoteMode.FULL_REMOTE,
        skills=Stack.from_list(["python"]),
        availability=_AVAILABILITY,
    )


def _make_tool(user_id: UUID, user: Optional[UserProfile]) -> SendDigestNowTool:
    assembler = DigestAssembler(
        user_profile_repository=FakeUserProfileRepository(user),
        mission_match_repository=FakeMissionMatchRepository([]),
        analyzed_post_repository=FakeAnalyzedPostRepository([]),
        raw_post_repository=FakeRawPostRepository({}),
        selector=DigestMissionSelector(),
        generator=DigestGenerator(),
    )
    send_digest_now = SendDigestNow(
        digest_assembler=assembler,
        renderer=FakeRenderer(),
        mailer=FakeMailer(),
        digest_history_repository=FakeDigestHistoryRepository(),
    )
    return SendDigestNowTool(identity_resolver=FakeIdentityResolver(user_id), send_digest_now=send_digest_now)


@pytest.mark.asyncio
async def test_send_digest_now_tool_returns_serialized_result() -> None:
    user_id = uuid4()
    tool = _make_tool(user_id, _make_user(user_id))

    payload = await tool.execute()

    assert payload == {
        "status": "sent",
        "missions_count": 0,
        "provider_message_id": "msg-123",
        "error_message": None,
    }
