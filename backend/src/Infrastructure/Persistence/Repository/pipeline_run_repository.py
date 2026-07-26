from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.Repository.pipeline_run_repository import PipelineRunRepository
from src.Domain.ValueObject.pipeline_enums import PipelineStatus
from src.Infrastructure.Persistence.exceptions import DatabaseError
from src.Infrastructure.Persistence.Mapper.pipeline_run_mapper import PipelineRunMapper
from src.Infrastructure.Persistence.SQLAlchemy.Models.pipeline_run_model import PipelineRunModel


class SqlAlchemyPipelineRunRepository(PipelineRunRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, run: PipelineRun) -> None:
        try:
            model = PipelineRunMapper.to_model(run)
            self._session.add(model)
            await self._session.flush()
        except IntegrityError as e:
            raise DatabaseError(str(e)) from e
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def get_by_id(self, run_id: UUID) -> Optional[PipelineRun]:
        try:
            model = await self._session.get(PipelineRunModel, run_id)
            return PipelineRunMapper.to_domain(model) if model else None
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def find_latest_for_user(self, user_id: UUID) -> Optional[PipelineRun]:
        try:
            result = await self._session.execute(
                select(PipelineRunModel)
                .where(PipelineRunModel.user_id == user_id)
                .order_by(PipelineRunModel.created_at.desc())
                .limit(1)
            )
            model = result.scalar_one_or_none()
            return PipelineRunMapper.to_domain(model) if model else None
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def find_running_for_user(self, user_id: UUID) -> Optional[PipelineRun]:
        try:
            result = await self._session.execute(
                select(PipelineRunModel)
                .where(
                    PipelineRunModel.user_id == user_id,
                    PipelineRunModel.status.in_([
                        PipelineStatus.PENDING.value,
                        PipelineStatus.RUNNING.value,
                    ]),
                )
                .limit(1)
            )
            model = result.scalar_one_or_none()
            return PipelineRunMapper.to_domain(model) if model else None
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e

    async def update(self, run: PipelineRun) -> None:
        try:
            model = PipelineRunMapper.to_model(run)
            await self._session.merge(model)
            await self._session.flush()
        except IntegrityError as e:
            raise DatabaseError(str(e)) from e
        except SQLAlchemyError as e:
            raise DatabaseError(str(e)) from e
