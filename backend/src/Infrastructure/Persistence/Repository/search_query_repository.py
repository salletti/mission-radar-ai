from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.Domain.Entity.search_query import SearchQuery
from src.Domain.Repository.search_query_repository import SearchQueryRepository
from src.Infrastructure.Persistence.exceptions import DatabaseError
from src.Infrastructure.Persistence.Mapper.search_query_mapper import SearchQueryMapper
from src.Infrastructure.Persistence.SQLAlchemy.Models.search_query_model import SearchQueryModel


class SqlAlchemySearchQueryRepository(SearchQueryRepository):
    """Doctrine-style repository: wraps AsyncSession, speaks Domain entities."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_many(self, queries: list[SearchQuery]) -> None:
        if not queries:
            return
        try:
            models = [SearchQueryMapper.to_model(q) for q in queries]
            self._session.add_all(models)
            await self._session.flush()
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def delete_by_profile(self, user_profile_id: UUID) -> None:
        try:
            await self._session.execute(
                delete(SearchQueryModel).where(
                    SearchQueryModel.user_profile_id == user_profile_id
                )
            )
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def get_by_profile(self, user_profile_id: UUID) -> list[SearchQuery]:
        try:
            result = await self._session.execute(
                select(SearchQueryModel)
                .where(SearchQueryModel.user_profile_id == user_profile_id)
                .order_by(SearchQueryModel.created_at.asc())
            )
            return [SearchQueryMapper.to_domain(m) for m in result.scalars()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def get_by_source(self, source: str) -> list[SearchQuery]:
        try:
            result = await self._session.execute(
                select(SearchQueryModel).where(SearchQueryModel.source == source)
            )
            return [SearchQueryMapper.to_domain(m) for m in result.scalars()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e
