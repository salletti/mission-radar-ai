from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.Domain.Entity.digest_history import DigestHistory
from src.Domain.Repository.digest_history_repository import DigestHistoryRepository
from src.Infrastructure.Persistence.Mapper.digest_history_mapper import DigestHistoryMapper
from src.Infrastructure.Persistence.SQLAlchemy.Models.digest_history_model import DigestHistoryModel
from src.Infrastructure.Persistence.exceptions import DatabaseError


class SqlAlchemyDigestHistoryRepository(DigestHistoryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, history: DigestHistory) -> None:
        try:
            model = DigestHistoryMapper.to_model(history)
            self._session.add(model)
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc

    async def find_by_user(self, user_id: UUID) -> list[DigestHistory]:
        try:
            stmt = (
                select(DigestHistoryModel)
                .where(DigestHistoryModel.user_id == user_id)
                .order_by(DigestHistoryModel.sent_at.desc())
            )
            result = await self._session.execute(stmt)
            models = result.scalars().all()
            return [DigestHistoryMapper.to_domain(m) for m in models]
        except Exception as exc:
            raise DatabaseError(str(exc)) from exc
