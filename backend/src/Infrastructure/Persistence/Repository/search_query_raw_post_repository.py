from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.Domain.Entity.search_query_raw_post import SearchQueryRawPost
from src.Domain.Repository.search_query_raw_post_repository import SearchQueryRawPostRepository
from src.Infrastructure.Persistence.exceptions import DatabaseError
from src.Infrastructure.Persistence.Mapper.search_query_raw_post_mapper import SearchQueryRawPostMapper
from src.Infrastructure.Persistence.SQLAlchemy.Models.search_query_raw_post_model import SearchQueryRawPostModel


class SqlAlchemySearchQueryRawPostRepository(SearchQueryRawPostRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, link: SearchQueryRawPost) -> None:
        try:
            model = SearchQueryRawPostMapper.to_model(link)
            self._session.add(model)
            await self._session.flush()
        except IntegrityError as e:
            raise DatabaseError(str(e)) from e
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def exists(self, search_query_id: UUID, raw_post_id: UUID) -> bool:
        try:
            result = await self._session.execute(
                select(
                    exists().where(
                        SearchQueryRawPostModel.search_query_id == search_query_id,
                        SearchQueryRawPostModel.raw_post_id == raw_post_id,
                    )
                )
            )
            return result.scalar()
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def find_by_search_query_id(self, search_query_id: UUID) -> list[SearchQueryRawPost]:
        try:
            result = await self._session.execute(
                select(SearchQueryRawPostModel)
                .where(SearchQueryRawPostModel.search_query_id == search_query_id)
                .order_by(SearchQueryRawPostModel.created_at.asc())
            )
            return [SearchQueryRawPostMapper.to_domain(m) for m in result.scalars().all()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def find_by_raw_post_id(self, raw_post_id: UUID) -> list[SearchQueryRawPost]:
        try:
            result = await self._session.execute(
                select(SearchQueryRawPostModel)
                .where(SearchQueryRawPostModel.raw_post_id == raw_post_id)
                .order_by(SearchQueryRawPostModel.created_at.asc())
            )
            return [SearchQueryRawPostMapper.to_domain(m) for m in result.scalars().all()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def find_by_search_query_ids(
        self, search_query_ids: list[UUID]
    ) -> list[SearchQueryRawPost]:
        if not search_query_ids:
            return []
        try:
            result = await self._session.execute(
                select(SearchQueryRawPostModel)
                .where(SearchQueryRawPostModel.search_query_id.in_(search_query_ids))
                .order_by(SearchQueryRawPostModel.created_at.asc())
            )
            return [SearchQueryRawPostMapper.to_domain(m) for m in result.scalars().all()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e
