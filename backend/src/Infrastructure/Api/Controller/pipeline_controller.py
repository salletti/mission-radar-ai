from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.Application.Exception.application_error import PipelineAlreadyRunningError, UserProfileNotFoundError
from src.Application.UseCase.start_mission_refresh import StartMissionRefresh
from src.Domain.ValueObject.pipeline_enums import PipelineTrigger
from src.Infrastructure.Api.Dependency.dependencies import get_current_user_profile_id
from src.Infrastructure.Api.Dependency.pipeline_dependencies import (
    get_pipeline_run_repository,
    get_start_mission_refresh,
)
from src.Infrastructure.Persistence.Repository.pipeline_run_repository import SqlAlchemyPipelineRunRepository

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


class PipelineRunResponse(BaseModel):
    id: UUID
    user_id: UUID
    pipeline_type: str
    trigger_type: str
    status: str
    current_step: str
    progress: float
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    error_message: Optional[str]
    step_outcomes: dict[str, str]
    created_at: datetime


@router.post(
    "/mission-refresh",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_200_OK,
)
async def start_mission_refresh(
    user_profile_id: UUID = Depends(get_current_user_profile_id),
    use_case: StartMissionRefresh = Depends(get_start_mission_refresh),
) -> PipelineRunResponse:
    """Triggers a new mission refresh pipeline for the authenticated user."""
    try:
        run = await use_case.execute(user_profile_id, PipelineTrigger.USER)
    except UserProfileNotFoundError:
        raise HTTPException(status_code=404, detail="User not found")
    except PipelineAlreadyRunningError:
        raise HTTPException(status_code=409, detail="A pipeline is already running for this user")

    return PipelineRunResponse(
        id=run.id,
        user_id=run.user_id,
        pipeline_type=run.pipeline_type.value,
        trigger_type=run.trigger_type.value,
        status=run.status.value,
        current_step=run.current_step.value,
        progress=run.progress,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error_message=run.error_message,
        step_outcomes={s.value: o.value for s, o in run.step_outcomes.items()},
        created_at=run.created_at,
    )


@router.get("/{pipeline_run_id}", response_model=PipelineRunResponse)
async def get_pipeline_run(
    pipeline_run_id: UUID,
    user_profile_id: UUID = Depends(get_current_user_profile_id),
    repo: SqlAlchemyPipelineRunRepository = Depends(get_pipeline_run_repository),
) -> PipelineRunResponse:
    """Returns the current state of a pipeline run owned by the authenticated user."""
    run = await repo.get_by_id(pipeline_run_id)
    if run is None or run.user_id != user_profile_id:
        raise HTTPException(status_code=404, detail="Pipeline run not found")

    return PipelineRunResponse(
        id=run.id,
        user_id=run.user_id,
        pipeline_type=run.pipeline_type.value,
        trigger_type=run.trigger_type.value,
        status=run.status.value,
        current_step=run.current_step.value,
        progress=run.progress,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error_message=run.error_message,
        step_outcomes={s.value: o.value for s, o in run.step_outcomes.items()},
        created_at=run.created_at,
    )
