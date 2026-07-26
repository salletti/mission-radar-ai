from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.Domain.Entity.external_identity import ExternalIdentity
from src.Domain.Repository.external_identity_repository import ExternalIdentityRepository
from src.Infrastructure.Persistence.exceptions import DatabaseError
from src.Infrastructure.Persistence.Mapper.external_identity_mapper import ExternalIdentityMapper
from src.Infrastructure.Persistence.SQLAlchemy.Models.external_identity_model import ExternalIdentityModel


class SqlAlchemyExternalIdentityRepository(ExternalIdentityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_provider_and_subject(self, provider: str, subject: str) -> Optional[ExternalIdentity]:
        try:
            result = await self._session.execute(
                select(ExternalIdentityModel).where(
                    ExternalIdentityModel.provider == provider,
                    ExternalIdentityModel.subject == subject,
                )
            )
            model = result.scalar_one_or_none()
            return ExternalIdentityMapper.to_domain(model) if model else None
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def save(self, identity: ExternalIdentity) -> None:
        try:
            model = ExternalIdentityMapper.to_model(identity)
            await self._session.merge(model)
            await self._session.flush()
        except IntegrityError as e:
            raise DatabaseError(str(e)) from e
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def list_for_user(self, user_profile_id: UUID) -> list[ExternalIdentity]:
        try:
            result = await self._session.execute(
                select(ExternalIdentityModel).where(
                    ExternalIdentityModel.user_profile_id == user_profile_id
                )
            )
            return [ExternalIdentityMapper.to_domain(model) for model in result.scalars().all()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e
