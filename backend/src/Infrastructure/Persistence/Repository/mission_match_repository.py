from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Infrastructure.Persistence.exceptions import DatabaseError
from src.Infrastructure.Persistence.Mapper.mission_match_mapper import MissionMatchMapper
from src.Infrastructure.Persistence.SQLAlchemy.Models.mission_match_model import MissionMatchModel


class SqlAlchemyMissionMatchRepository(MissionMatchRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, match: MissionMatch) -> None:
        try:
            model = MissionMatchMapper.to_model(match)
            await self._session.merge(model)
            await self._session.flush()
        except IntegrityError as e:
            raise DatabaseError(str(e)) from e
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def save_many(self, matches: list[MissionMatch]) -> None:
        if not matches:
            return
        try:
            for match in matches:
                await self._session.merge(MissionMatchMapper.to_model(match))
            await self._session.flush()
        except IntegrityError as e:
            raise DatabaseError(str(e)) from e
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def get_by_id(self, match_id: UUID) -> Optional[MissionMatch]:
        try:
            model = await self._session.get(MissionMatchModel, match_id)
            return MissionMatchMapper.to_domain(model) if model else None
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def get_by_user(self, user_id: UUID) -> list[MissionMatch]:
        try:
            result = await self._session.execute(
                select(MissionMatchModel).where(MissionMatchModel.user_profile_id == user_id)
            )
            return [MissionMatchMapper.to_domain(m) for m in result.scalars().all()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def get_by_post(self, post_id: UUID) -> list[MissionMatch]:
        try:
            result = await self._session.execute(
                select(MissionMatchModel).where(MissionMatchModel.analyzed_post_id == post_id)
            )
            return [MissionMatchMapper.to_domain(m) for m in result.scalars().all()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def get_best_matches(self, user_id: UUID, limit: int) -> list[MissionMatch]:
        try:
            result = await self._session.execute(
                select(MissionMatchModel)
                .where(MissionMatchModel.user_profile_id == user_id)
                .order_by(MissionMatchModel.global_score.desc())
                .limit(limit)
            )
            return [MissionMatchMapper.to_domain(m) for m in result.scalars().all()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def delete_user_matches(self, user_id: UUID) -> None:
        try:
            await self._session.execute(
                delete(MissionMatchModel).where(MissionMatchModel.user_profile_id == user_id)
            )
            await self._session.flush()
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e
