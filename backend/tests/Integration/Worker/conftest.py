"""Fixtures for Worker integration tests — requires running PostgreSQL."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest_asyncio
from sqlalchemy import text

from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.Entity.search_query import SearchQuery
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.pipeline_enums import PipelineStatus, PipelineStep, PipelineTrigger, PipelineType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack
from src.Infrastructure.Config.database import AsyncSessionLocal
from src.Infrastructure.Persistence.Repository.pipeline_run_repository import SqlAlchemyPipelineRunRepository
from src.Infrastructure.Persistence.Repository.search_query_repository import SqlAlchemySearchQueryRepository
from src.Infrastructure.Persistence.Repository.user_profile_repository import SqlAlchemyUserProfileRepository
from tests.Integration.Repository.conftest import make_user_profile

_AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)


@pytest_asyncio.fixture(autouse=True)
async def cleanup_worker_tables() -> None:
    """Truncate worker-related tables before and after each test."""
    async with AsyncSessionLocal() as session:
        await session.execute(text("TRUNCATE TABLE raw_posts CASCADE"))
        await session.execute(text("TRUNCATE TABLE user_profiles CASCADE"))
        await session.commit()
    yield
    async with AsyncSessionLocal() as session:
        await session.execute(text("TRUNCATE TABLE raw_posts CASCADE"))
        await session.execute(text("TRUNCATE TABLE user_profiles CASCADE"))
        await session.commit()


@pytest_asyncio.fixture
async def search_query_id() -> str:
    """Persists a UserProfile + SearchQuery and returns the SearchQuery id as a string."""
    profile = make_user_profile()
    query = SearchQuery(
        id=uuid4(),
        user_profile_id=profile.id,
        query="python freelance paris",
        limit=50,
        source="linkedin",
    )
    async with AsyncSessionLocal() as session:
        user_repo = SqlAlchemyUserProfileRepository(session)
        await user_repo.save(profile)
        sq_repo = SqlAlchemySearchQueryRepository(session)
        await sq_repo.save_many([query])
        await session.commit()
    return str(query.id)


@pytest_asyncio.fixture
async def user_with_query() -> tuple[UserProfile, SearchQuery]:
    """Persists a UserProfile + SearchQuery, returns both domain objects."""
    profile = make_user_profile()
    query = SearchQuery(
        id=uuid4(),
        user_profile_id=profile.id,
        query="python freelance paris",
        limit=50,
        source="linkedin",
    )
    async with AsyncSessionLocal() as session:
        user_repo = SqlAlchemyUserProfileRepository(session)
        await user_repo.save(profile)
        sq_repo = SqlAlchemySearchQueryRepository(session)
        await sq_repo.save_many([query])
        await session.commit()
    return profile, query


@pytest_asyncio.fixture
async def pending_pipeline_run(user_with_query: tuple[UserProfile, SearchQuery]) -> PipelineRun:
    """Persists a PENDING PipelineRun linked to the user, returns the domain object."""
    profile, _ = user_with_query
    run = PipelineRun(
        id=uuid4(),
        user_id=profile.id,
        pipeline_type=PipelineType.MISSION_REFRESH,
        trigger_type=PipelineTrigger.USER,
        status=PipelineStatus.PENDING,
        current_step=PipelineStep.COLLECT,
        progress=0.0,
    )
    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyPipelineRunRepository(session)
        await repo.save(run)
        await session.commit()
    return run
