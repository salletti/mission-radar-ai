from typing import Optional
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.Domain.Entity.raw_post import RawPost
from src.Domain.Repository.raw_post_repository import RawPostRepository
from src.Infrastructure.Persistence.exceptions import DatabaseError
from src.Infrastructure.Persistence.Mapper.raw_post_mapper import RawPostMapper
from src.Infrastructure.Persistence.SQLAlchemy.Models.raw_post_model import RawPostModel


class SqlAlchemyRawPostRepository(RawPostRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, raw_post: RawPost) -> None:
        try:
            model = RawPostMapper.to_model(raw_post)
            await self._session.merge(model)
            await self._session.flush()
        except IntegrityError as e:
            raise DatabaseError(str(e)) from e
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def get_by_id(self, raw_post_id: UUID) -> Optional[RawPost]:
        try:
            model = await self._session.get(RawPostModel, raw_post_id)
            return RawPostMapper.to_domain(model) if model else None
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def exists_by_external_id(self, source: str, external_id: str) -> bool:
        try:
            result = await self._session.execute(
                select(
                    exists().where(
                        RawPostModel.source == source,
                        RawPostModel.external_id == external_id,
                    )
                )
            )
            return result.scalar()
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def save_many(self, posts: list[RawPost]) -> None:
        if not posts:
            return
        try:
            models = [RawPostMapper.to_model(p) for p in posts]
            self._session.add_all(models)
            await self._session.flush()
        except IntegrityError as e:
            raise DatabaseError(str(e)) from e
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def get_by_source_and_external_id(self, source: str, external_id: str) -> Optional[RawPost]:
        try:
            result = await self._session.execute(
                select(RawPostModel).where(
                    RawPostModel.source == source,
                    RawPostModel.external_id == external_id,
                )
            )
            model = result.scalar_one_or_none()
            return RawPostMapper.to_domain(model) if model else None
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def list_recent(self, limit: int) -> list[RawPost]:
        try:
            result = await self._session.execute(
                select(RawPostModel).order_by(RawPostModel.scraped_at.desc()).limit(limit)
            )
            return [RawPostMapper.to_domain(m) for m in result.scalars().all()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def find_by_ids(self, ids: list[UUID]) -> list[RawPost]:
        if not ids:
            return []
        try:
            result = await self._session.execute(
                select(RawPostModel).where(RawPostModel.id.in_(ids))
            )
            return [RawPostMapper.to_domain(m) for m in result.scalars().all()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e
