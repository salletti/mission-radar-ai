from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Infrastructure.Persistence.exceptions import DatabaseError
from src.Infrastructure.Persistence.Mapper.analyzed_post_mapper import AnalyzedPostMapper
from src.Infrastructure.Persistence.SQLAlchemy.Models.analyzed_post_model import AnalyzedPostModel


class SqlAlchemyAnalyzedPostRepository(AnalyzedPostRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, analyzed_post: AnalyzedPost) -> None:
        try:
            model = AnalyzedPostMapper.to_model(analyzed_post)
            await self._session.merge(model)
            await self._session.flush()
        except IntegrityError as e:
            raise DatabaseError(str(e)) from e
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def get_by_id(self, post_id: UUID) -> Optional[AnalyzedPost]:
        try:
            model = await self._session.get(AnalyzedPostModel, post_id)
            return AnalyzedPostMapper.to_domain(model) if model else None
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def get_by_raw_post_id(self, raw_post_id: UUID) -> Optional[AnalyzedPost]:
        try:
            result = await self._session.execute(
                select(AnalyzedPostModel).where(AnalyzedPostModel.raw_post_id == raw_post_id)
            )
            model = result.scalar_one_or_none()
            return AnalyzedPostMapper.to_domain(model) if model else None
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def list_today_missions(self) -> list[AnalyzedPost]:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            result = await self._session.execute(
                select(AnalyzedPostModel)
                .where(AnalyzedPostModel.created_at >= today_start)
                .order_by(AnalyzedPostModel.created_at.desc())
            )
            return [AnalyzedPostMapper.to_domain(m) for m in result.scalars().all()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def list_missions(self, limit: int) -> list[AnalyzedPost]:
        try:
            result = await self._session.execute(
                select(AnalyzedPostModel)
                .order_by(AnalyzedPostModel.created_at.desc())
                .limit(limit)
            )
            return [AnalyzedPostMapper.to_domain(m) for m in result.scalars().all()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def find_by_raw_post_ids(self, raw_post_ids: list[UUID]) -> list[AnalyzedPost]:
        if not raw_post_ids:
            return []
        try:
            result = await self._session.execute(
                select(AnalyzedPostModel).where(
                    AnalyzedPostModel.raw_post_id.in_(raw_post_ids)
                )
            )
            return [AnalyzedPostMapper.to_domain(m) for m in result.scalars().all()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def find_by_ids(self, ids: list[UUID]) -> list[AnalyzedPost]:
        if not ids:
            return []
        try:
            result = await self._session.execute(
                select(AnalyzedPostModel).where(AnalyzedPostModel.id.in_(ids))
            )
            return [AnalyzedPostMapper.to_domain(m) for m in result.scalars().all()]
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e
