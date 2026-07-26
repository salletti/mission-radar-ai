from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from src.Domain.Entity.pipeline_run import PipelineRun


class PipelineRunRepository(ABC):
    """Domain interface for PipelineRun persistence. Implemented in Infrastructure/."""

    @abstractmethod
    async def save(self, run: PipelineRun) -> None: ...

    @abstractmethod
    async def get_by_id(self, run_id: UUID) -> Optional[PipelineRun]: ...

    @abstractmethod
    async def find_latest_for_user(self, user_id: UUID) -> Optional[PipelineRun]: ...

    @abstractmethod
    async def find_running_for_user(self, user_id: UUID) -> Optional[PipelineRun]: ...

    @abstractmethod
    async def update(self, run: PipelineRun) -> None: ...
