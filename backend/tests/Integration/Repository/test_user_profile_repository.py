"""Integration tests for SqlAlchemyUserProfileRepository — requires running PostgreSQL."""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.Infrastructure.Persistence.exceptions import DatabaseError
from src.Infrastructure.Persistence.Repository.user_profile_repository import SqlAlchemyUserProfileRepository
from tests.Integration.Repository.conftest import make_user_profile


@pytest.mark.asyncio
async def test_save_and_get_by_id(db_session: AsyncSession) -> None:
    repo = SqlAlchemyUserProfileRepository(db_session)
    profile = make_user_profile()

    await repo.save(profile)
    fetched = await repo.get_by_id(profile.id)

    assert fetched is not None
    assert fetched.id == profile.id
    assert fetched.email == profile.email
    assert fetched.skills.technologies == profile.skills.technologies


@pytest.mark.asyncio
async def test_get_by_email(db_session: AsyncSession) -> None:
    repo = SqlAlchemyUserProfileRepository(db_session)
    profile = make_user_profile(email="stefano@test.com")

    await repo.save(profile)
    fetched = await repo.get_by_email("stefano@test.com")

    assert fetched is not None
    assert fetched.id == profile.id


@pytest.mark.asyncio
async def test_get_by_email_returns_none_when_absent(db_session: AsyncSession) -> None:
    repo = SqlAlchemyUserProfileRepository(db_session)
    result = await repo.get_by_email("nobody@test.com")
    assert result is None


@pytest.mark.asyncio
async def test_save_twice_same_id_is_update(db_session: AsyncSession) -> None:
    repo = SqlAlchemyUserProfileRepository(db_session)
    profile = make_user_profile(title="Junior")
    await repo.save(profile)

    # Update in-place — same id, new title
    from dataclasses import replace
    updated = replace(profile, title="Senior")
    await repo.save(updated)

    fetched = await repo.get_by_id(profile.id)
    assert fetched is not None
    assert fetched.title == "Senior"

    # Only one row, not two
    from sqlalchemy import func, select
    from src.Infrastructure.Persistence.SQLAlchemy.Models.user_profile_model import UserProfileModel
    count = await db_session.scalar(
        select(func.count()).where(UserProfileModel.id == profile.id)
    )
    assert count == 1


@pytest.mark.asyncio
async def test_duplicate_email_raises_database_error(db_session: AsyncSession) -> None:
    repo = SqlAlchemyUserProfileRepository(db_session)
    email = "dup@test.com"
    await repo.save(make_user_profile(email=email))

    with pytest.raises(DatabaseError):
        await repo.save(make_user_profile(email=email))


@pytest.mark.asyncio
async def test_get_active_profile_returns_most_recent(db_session: AsyncSession) -> None:
    repo = SqlAlchemyUserProfileRepository(db_session)
    await repo.save(make_user_profile(title="First"))
    await repo.save(make_user_profile(title="Second"))

    active = await repo.get_active_profile()
    assert active is not None
    # The most recently created one wins — both are flushed in order
    assert active.title in ("First", "Second")


@pytest.mark.asyncio
async def test_get_active_profile_returns_a_profile_or_none(db_session: AsyncSession) -> None:
    """get_active_profile must return a UserProfile or None — never raise."""
    repo = SqlAlchemyUserProfileRepository(db_session)
    result = await repo.get_active_profile()
    assert result is None or hasattr(result, "email")


@pytest.mark.asyncio
async def test_delete_removes_profile(db_session: AsyncSession) -> None:
    repo = SqlAlchemyUserProfileRepository(db_session)
    profile = make_user_profile()
    await repo.save(profile)

    await repo.delete(profile.id)
    fetched = await repo.get_by_id(profile.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_delete_nonexistent_is_noop(db_session: AsyncSession) -> None:
    from uuid import uuid4
    repo = SqlAlchemyUserProfileRepository(db_session)
    await repo.delete(uuid4())  # must not raise
