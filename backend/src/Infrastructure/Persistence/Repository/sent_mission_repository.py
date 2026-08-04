from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.Domain.Repository.sent_mission_repository import SentMissionRepository
from src.Infrastructure.Persistence.exceptions import DatabaseError
from src.Infrastructure.Persistence.SQLAlchemy.Models.sent_mission_model import SentMissionModel


class SqlAlchemySentMissionRepository(SentMissionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_sent_analyzed_post_ids(self, user_id: UUID) -> set[UUID]:
        try:
            result = await self._session.execute(
                select(SentMissionModel.analyzed_post_id).where(SentMissionModel.user_profile_id == user_id)
            )
            return set(result.scalars().all())
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def save_many(self, user_id: UUID, analyzed_post_ids: list[UUID], sent_at: datetime) -> None:
        if not analyzed_post_ids:
            return
        try:
            for analyzed_post_id in analyzed_post_ids:
                self._session.add(
                    SentMissionModel(
                        user_profile_id=user_id,
                        analyzed_post_id=analyzed_post_id,
                        sent_at=sent_at,
                    )
                )
            await self._session.flush()
        except IntegrityError as e:
            raise DatabaseError(str(e)) from e
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e
