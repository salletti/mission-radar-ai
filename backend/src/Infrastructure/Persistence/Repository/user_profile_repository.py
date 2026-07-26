from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Infrastructure.Persistence.exceptions import DatabaseError
from src.Infrastructure.Persistence.Mapper.user_profile_mapper import UserProfileMapper
from src.Infrastructure.Persistence.SQLAlchemy.Models.user_profile_model import UserProfileModel


class SqlAlchemyUserProfileRepository(UserProfileRepository):
    """Doctrine-style repository: wraps AsyncSession, speaks Domain entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, profile: UserProfile) -> None:
        try:
            model = UserProfileMapper.to_model(profile)
            await self._session.merge(model)
            await self._session.flush()
        except IntegrityError as e:
            raise DatabaseError(str(e)) from e
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def get_by_id(self, profile_id: UUID) -> Optional[UserProfile]:
        try:
            model = await self._session.get(UserProfileModel, profile_id)
            return UserProfileMapper.to_domain(model) if model else None
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def get_by_email(self, email: str) -> Optional[UserProfile]:
        try:
            result = await self._session.execute(
                select(UserProfileModel).where(UserProfileModel.email == email)
            )
            model = result.scalar_one_or_none()
            return UserProfileMapper.to_domain(model) if model else None
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def get_active_profile(self) -> Optional[UserProfile]:
        """Returns the most recently created profile (MVP single-user context)."""
        try:
            result = await self._session.execute(
                select(UserProfileModel).order_by(UserProfileModel.created_at.desc()).limit(1)
            )
            model = result.scalar_one_or_none()
            return UserProfileMapper.to_domain(model) if model else None
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def delete(self, profile_id: UUID) -> None:
        try:
            model = await self._session.get(UserProfileModel, profile_id)
            if model:
                await self._session.delete(model)
                await self._session.flush()
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e
