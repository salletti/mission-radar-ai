"""Integration tests for SQLAlchemy models — requires running Docker PostgreSQL."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.Infrastructure.Persistence.SQLAlchemy.Models.analyzed_post_model import AnalyzedPostModel
from src.Infrastructure.Persistence.SQLAlchemy.Models.mission_match_model import MissionMatchModel
from src.Infrastructure.Persistence.SQLAlchemy.Models.raw_post_model import RawPostModel
from src.Infrastructure.Persistence.SQLAlchemy.Models.user_profile_model import UserProfileModel

NOW = datetime.now(timezone.utc)
AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)


def make_profile(**kwargs) -> UserProfileModel:
    defaults = dict(
        id=uuid4(),
        email=f"{uuid4()}@test.com",
        full_name="Test User",
        title="Senior Python Engineer",
        years_experience=10,
        preferred_contract_type="freelance",
        target_tjm=700.0,
        preferred_remote_mode="full_remote",
        location="Paris",
        availability=AVAILABILITY,
        skills=["Python", "FastAPI"],
    )
    return UserProfileModel(**{**defaults, **kwargs})


def make_raw_post(**kwargs) -> RawPostModel:
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
    return RawPostModel(**{**defaults, **kwargs})


def make_analyzed_post(raw_post_id, **kwargs) -> AnalyzedPostModel:
    defaults = dict(
        id=uuid4(),
        raw_post_id=raw_post_id,
        summary="Mission Python full remote.",
        detected_stack=["fastapi", "python"],
        detected_tjm_amount=700.0,
        detected_contract_type="freelance",
        detected_remote_mode="full_remote",
        title="Lead Python Engineer",
        company=None,
        location=None,
        seniority="senior",
    )
    return AnalyzedPostModel(**{**defaults, **kwargs})


def make_match(user_profile_id, analyzed_post_id, **kwargs) -> MissionMatchModel:
    defaults = dict(
        id=uuid4(),
        user_profile_id=user_profile_id,
        analyzed_post_id=analyzed_post_id,
        semantic_score=0.85,
        stack_score=0.80,
        contract_score=1.0,
        tjm_score=0.90,
        remote_score=1.0,
        global_score=0.875,
    )
    return MissionMatchModel(**{**defaults, **kwargs})


@pytest.mark.asyncio
async def test_insert_user_profile(db_session: AsyncSession) -> None:
    profile = make_profile(email="alice@test.com")
    db_session.add(profile)
    await db_session.flush()

    result = await db_session.scalar(
        select(UserProfileModel).where(UserProfileModel.id == profile.id)
    )
    assert result is not None
    assert result.email == "alice@test.com"
    assert result.preferred_contract_type == "freelance"
    assert result.skills == ["Python", "FastAPI"]
    assert result.created_at is not None


@pytest.mark.asyncio
async def test_email_unique_constraint(db_session: AsyncSession) -> None:
    shared_email = "duplicate@test.com"
    db_session.add(make_profile(email=shared_email))
    await db_session.flush()

    db_session.add(make_profile(email=shared_email))
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_insert_raw_post(db_session: AsyncSession) -> None:
    post = make_raw_post()
    db_session.add(post)
    await db_session.flush()

    result = await db_session.scalar(
        select(RawPostModel).where(RawPostModel.id == post.id)
    )
    assert result is not None
    assert result.source == "linkedin"
    assert result.created_at is not None


@pytest.mark.asyncio
async def test_source_external_id_unique(db_session: AsyncSession) -> None:
    post1 = make_raw_post(source="linkedin", external_id="same_post_id")
    post2 = make_raw_post(source="linkedin", external_id="same_post_id")
    db_session.add(post1)
    await db_session.flush()

    db_session.add(post2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_insert_analyzed_post(db_session: AsyncSession) -> None:
    raw = make_raw_post()
    db_session.add(raw)
    await db_session.flush()

    analyzed = make_analyzed_post(raw_post_id=raw.id)
    db_session.add(analyzed)
    await db_session.flush()

    result = await db_session.scalar(
        select(AnalyzedPostModel).where(AnalyzedPostModel.id == analyzed.id)
    )
    assert result is not None
    assert result.summary == "Mission Python full remote."
    assert result.detected_tjm_amount == pytest.approx(700.0)
    assert result.title == "Lead Python Engineer"
    assert result.seniority == "senior"


@pytest.mark.asyncio
async def test_insert_mission_match(db_session: AsyncSession) -> None:
    profile = make_profile()
    raw = make_raw_post()
    db_session.add_all([profile, raw])
    await db_session.flush()

    analyzed = make_analyzed_post(raw_post_id=raw.id)
    db_session.add(analyzed)
    await db_session.flush()

    match = make_match(user_profile_id=profile.id, analyzed_post_id=analyzed.id)
    db_session.add(match)
    await db_session.flush()

    result = await db_session.scalar(
        select(MissionMatchModel).where(MissionMatchModel.id == match.id)
    )
    assert result is not None
    assert result.global_score == pytest.approx(0.875)
    assert result.semantic_score == pytest.approx(0.85)


@pytest.mark.asyncio
async def test_mission_match_unique_constraint(db_session: AsyncSession) -> None:
    profile = make_profile()
    raw = make_raw_post()
    db_session.add_all([profile, raw])
    await db_session.flush()

    analyzed = make_analyzed_post(raw_post_id=raw.id)
    db_session.add(analyzed)
    await db_session.flush()

    match1 = make_match(user_profile_id=profile.id, analyzed_post_id=analyzed.id)
    db_session.add(match1)
    await db_session.flush()

    match2 = make_match(user_profile_id=profile.id, analyzed_post_id=analyzed.id)
    db_session.add(match2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_relationship_raw_to_analyzed(db_session: AsyncSession) -> None:
    raw = make_raw_post()
    db_session.add(raw)
    await db_session.flush()

    analyzed = make_analyzed_post(raw_post_id=raw.id)
    db_session.add(analyzed)
    await db_session.flush()

    await db_session.refresh(raw, ["analyzed_post"])
    assert raw.analyzed_post is not None
    assert raw.analyzed_post.id == analyzed.id


@pytest.mark.asyncio
async def test_relationship_profile_to_matches(db_session: AsyncSession) -> None:
    profile = make_profile()
    raw1, raw2 = make_raw_post(), make_raw_post()
    db_session.add_all([profile, raw1, raw2])
    await db_session.flush()

    analyzed1 = make_analyzed_post(raw_post_id=raw1.id)
    analyzed2 = make_analyzed_post(raw_post_id=raw2.id)
    db_session.add_all([analyzed1, analyzed2])
    await db_session.flush()

    db_session.add_all([
        make_match(user_profile_id=profile.id, analyzed_post_id=analyzed1.id),
        make_match(user_profile_id=profile.id, analyzed_post_id=analyzed2.id),
    ])
    await db_session.flush()

    await db_session.refresh(profile, ["mission_matches"])
    assert len(profile.mission_matches) == 2
