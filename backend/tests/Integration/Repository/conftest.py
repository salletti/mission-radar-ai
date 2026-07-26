"""Shared fixtures and Domain entity factories for Repository integration tests."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.Entity.raw_post import RawPost
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.match_score import MatchScore
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack
from src.Infrastructure.Config.database import AsyncSessionLocal

NOW = datetime.now(timezone.utc)
AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Transactional fixture — rolls back after each test for full isolation."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


def make_user_profile(**kwargs) -> UserProfile:
    defaults = dict(
        id=uuid4(),
        email=f"{uuid4()}@test.com",
        full_name="Test User",
        title="Senior Python Engineer",
        years_experience=10,
        preferred_contract_type=ContractType.FREELANCE,
        target_tjm=700.0,
        preferred_remote_mode=RemoteMode.FULL_REMOTE,
        location="Paris",
        availability=AVAILABILITY,
        skills=Stack.from_list(["Python", "FastAPI"]),
    )
    return UserProfile(**{**defaults, **kwargs})


def make_raw_post(**kwargs) -> RawPost:
    uid = uuid4()
    defaults = dict(
        id=uuid4(),
        source="linkedin",
        external_id=str(uid),
        author_name="Author Test",
        author_url="https://linkedin.com/in/test",
        content="Mission Python freelance remote TJM 700€/j #freelance",
        post_url=f"https://linkedin.com/posts/{uid}",
        published_at=NOW,
        scraped_at=NOW,
    )
    return RawPost(**{**defaults, **kwargs})


def make_analyzed_post(raw_post_id, **kwargs) -> AnalyzedPost:
    defaults = dict(
        id=uuid4(),
        raw_post_id=raw_post_id,
        summary="Mission Python full remote.",
        detected_stack=("fastapi", "python"),
        detected_tjm=700.0,
        detected_contract_type=ContractType.FREELANCE,
        detected_remote_mode=RemoteMode.FULL_REMOTE,
        title="Lead Python Engineer",
        company=None,
        location=None,
        seniority="senior",
    )
    return AnalyzedPost(**{**defaults, **kwargs})


def make_mission_match(user_profile_id, analyzed_post_id, **kwargs) -> MissionMatch:
    score = MatchScore(
        semantic_score=kwargs.pop("semantic_score", 0.85),
        contract_score=kwargs.pop("contract_score", 1.0),
        remote_score=kwargs.pop("remote_score", 1.0),
        tjm_score=kwargs.pop("tjm_score", 0.90),
    )
    # global_score kwarg is ignored — derived from MatchScore.final_score
    kwargs.pop("global_score", None)
    kwargs.pop("stack_score", None)
    kwargs.pop("updated_at", None)
    return MissionMatch(
        id=kwargs.pop("id", uuid4()),
        user_profile_id=user_profile_id,
        analyzed_post_id=analyzed_post_id,
        match_score=score,
        created_at=kwargs.pop("created_at", NOW),
    )
