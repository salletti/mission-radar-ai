from abc import ABC, abstractmethod
from uuid import UUID


class PipelineDispatcherGateway(ABC):
    """Dispatches pipeline tasks to the async worker layer. Implemented in Infrastructure/."""

    @abstractmethod
    def run_mission_refresh(self, pipeline_run_id: UUID, user_id: UUID) -> None: ...
