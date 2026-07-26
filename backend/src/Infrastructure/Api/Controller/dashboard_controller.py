from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.Application.DTO.get_activity_history_query import GetActivityHistoryQuery
from src.Application.DTO.get_mission_details_query import GetMissionDetailsQuery
from src.Application.DTO.get_mission_history_query import GetMissionHistoryQuery
from src.Application.DTO.get_today_missions_query import GetTodayMissionsQuery
from src.Application.UseCase.get_activity_history import GetActivityHistory
from src.Application.UseCase.get_dashboard_summary import GetDashboardSummary
from src.Application.UseCase.get_mission_details import GetMissionDetails
from src.Application.UseCase.get_mission_history import GetMissionHistory
from src.Application.UseCase.get_today_missions import GetTodayMissions
from src.Domain.Exception.domain_exceptions import MissionMatchNotFoundError
from src.Infrastructure.Api.Dependency.dependencies import (
    get_activity_history_use_case,
    get_current_user_profile_id,
    get_dashboard_summary_use_case,
    get_mission_details_use_case,
    get_mission_history_use_case,
    get_today_missions_use_case,
)
from src.Infrastructure.Persistence.exceptions import DatabaseError

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------------
# Pydantic response schemas (inline — project convention)
# ---------------------------------------------------------------------------


class ScoreDetailsResponse(BaseModel):
    semantic: float
    contract: float
    tjm: float
    remote: float


class TodayMissionResponse(BaseModel):
    mission_match_id: UUID
    analyzed_post_id: UUID
    raw_post_id: UUID
    author_name: str
    content_excerpt: str
    post_url: str
    detected_stack: list[str]
    detected_contract_type: str
    detected_remote_mode: str
    global_score: float
    score_details: ScoreDetailsResponse
    detected_tjm: Optional[float]
    title: Optional[str]
    company: Optional[str]
    location: Optional[str]


class ScoreBreakdownResponse(BaseModel):
    skills: Optional[float] = None
    experience: Optional[float] = None
    location: Optional[float] = None
    contract: Optional[float] = None
    daily_rate: Optional[float] = None


class ExplanationResponse(BaseModel):
    score_breakdown: ScoreBreakdownResponse
    matching_reasons: list[str]
    warnings: list[str]
    strong_points: list[str]
    missing_skills: list[str]
    recommendations: list[str]


class MissionMatchDetailResponse(BaseModel):
    mission_match_id: UUID
    analyzed_post_id: UUID
    raw_post_id: UUID
    author_name: str
    author_url: str
    content: str
    post_url: str
    published_at: datetime
    title: Optional[str]
    company: Optional[str]
    location: Optional[str]
    summary: str
    seniority: Optional[str]
    detected_stack: list[str]
    detected_contract_type: str
    detected_remote_mode: str
    detected_tjm: Optional[float]
    global_score: float
    score_details: ScoreDetailsResponse
    matched_at: datetime
    matched_skills: list[str]
    missing_skills: list[str]
    explanation: ExplanationResponse


class DashboardKpisResponse(BaseModel):
    total_missions: int
    new_today: int
    average_score: int
    last_refresh: datetime | None
    pipeline_status: str | None


class PipelineHealthResponse(BaseModel):
    status: str
    last_pipeline_duration_seconds: float | None


class DashboardSummaryResponse(BaseModel):
    kpis: DashboardKpisResponse
    health: PipelineHealthResponse


class ActivityEventResponse(BaseModel):
    type: str
    occurred_at: datetime
    title: str
    description: str
    score: int
    mission_match_id: UUID | None = None
    digest_history_id: UUID | None = None


class ActivityHistoryPageResponse(BaseModel):
    items: list[ActivityEventResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Endpoints — order matters: literal paths before {param}
# ---------------------------------------------------------------------------


@router.get("/missions/today", response_model=list[TodayMissionResponse])
async def get_today_missions(
    user_profile_id: UUID = Depends(get_current_user_profile_id),
    min_score: float = 0.5,
    limit: int = 20,
    use_case: GetTodayMissions = Depends(get_today_missions_use_case),
) -> list[TodayMissionResponse]:
    """Returns today's top-scored missions for a user, sorted by match score."""
    try:
        missions = await use_case.execute(
            GetTodayMissionsQuery(
                user_profile_id=user_profile_id,
                min_score=min_score,
                limit=limit,
            )
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Database error")

    return [
        TodayMissionResponse(
            mission_match_id=m.mission_match_id,
            analyzed_post_id=m.analyzed_post_id,
            raw_post_id=m.raw_post_id,
            author_name=m.author_name,
            content_excerpt=m.content_excerpt,
            post_url=m.post_url,
            detected_stack=list(m.detected_stack),
            detected_contract_type=m.detected_contract_type,
            detected_remote_mode=m.detected_remote_mode,
            global_score=m.global_score,
            score_details=ScoreDetailsResponse(**m.score_details),
            detected_tjm=m.detected_tjm,
            title=m.title,
            company=m.company,
            location=m.location,
        )
        for m in missions
    ]


@router.get("/history", response_model=ActivityHistoryPageResponse)
async def get_activity_history(
    user_profile_id: UUID = Depends(get_current_user_profile_id),
    limit: int = 20,
    offset: int = 0,
    use_case: GetActivityHistory = Depends(get_activity_history_use_case),
) -> ActivityHistoryPageResponse:
    """Returns a paginated activity timeline for a user, sorted newest first."""
    try:
        page = await use_case.execute(
            GetActivityHistoryQuery(
                user_profile_id=user_profile_id,
                limit=limit,
                offset=offset,
            )
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Database error")

    return ActivityHistoryPageResponse(
        items=[
            ActivityEventResponse(
                type=event.type,
                occurred_at=event.occurred_at,
                title=event.title,
                description=event.description,
                score=event.score,
                mission_match_id=event.mission_match_id,
                digest_history_id=event.digest_history_id,
            )
            for event in page.items
        ],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/missions/history", response_model=list[TodayMissionResponse])
async def get_mission_history(
    user_profile_id: UUID = Depends(get_current_user_profile_id),
    min_score: float = 0.0,
    limit: int = 50,
    offset: int = 0,
    use_case: GetMissionHistory = Depends(get_mission_history_use_case),
) -> list[TodayMissionResponse]:
    """Returns a paginated history of all mission matches for a user, sorted newest first."""
    try:
        missions = await use_case.execute(
            GetMissionHistoryQuery(
                user_profile_id=user_profile_id,
                min_score=min_score,
                limit=limit,
                offset=offset,
            )
        )
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Database error")

    return [
        TodayMissionResponse(
            mission_match_id=m.mission_match_id,
            analyzed_post_id=m.analyzed_post_id,
            raw_post_id=m.raw_post_id,
            author_name=m.author_name,
            content_excerpt=m.content_excerpt,
            post_url=m.post_url,
            detected_stack=list(m.detected_stack),
            detected_contract_type=m.detected_contract_type,
            detected_remote_mode=m.detected_remote_mode,
            global_score=m.global_score,
            score_details=ScoreDetailsResponse(**m.score_details),
            detected_tjm=m.detected_tjm,
            title=m.title,
            company=m.company,
            location=m.location,
        )
        for m in missions
    ]


@router.get("/missions/{mission_match_id}", response_model=MissionMatchDetailResponse)
async def get_mission_detail(
    mission_match_id: UUID,
    user_profile_id: UUID = Depends(get_current_user_profile_id),
    use_case: GetMissionDetails = Depends(get_mission_details_use_case),
) -> MissionMatchDetailResponse:
    """Returns the full detail of a single mission match."""
    try:
        detail = await use_case.execute(
            GetMissionDetailsQuery(
                mission_match_id=mission_match_id,
                user_profile_id=user_profile_id,
            )
        )
    except MissionMatchNotFoundError:
        raise HTTPException(status_code=404, detail="Mission not found")
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Database error")

    return MissionMatchDetailResponse(
        mission_match_id=detail.mission_match_id,
        analyzed_post_id=detail.analyzed_post_id,
        raw_post_id=detail.raw_post_id,
        author_name=detail.author_name,
        author_url=detail.author_url,
        content=detail.content,
        post_url=detail.post_url,
        published_at=detail.published_at,
        title=detail.title,
        company=detail.company,
        location=detail.location,
        summary=detail.summary,
        seniority=detail.seniority,
        detected_stack=list(detail.detected_stack),
        detected_contract_type=detail.detected_contract_type,
        detected_remote_mode=detail.detected_remote_mode,
        detected_tjm=detail.detected_tjm,
        global_score=detail.global_score,
        score_details=ScoreDetailsResponse(**detail.score_details),
        matched_at=detail.matched_at,
        matched_skills=list(detail.matched_skills),
        missing_skills=list(detail.missing_skills),
        explanation=ExplanationResponse(
            score_breakdown=ScoreBreakdownResponse(
                skills=detail.explanation.score_breakdown.skills,
                experience=detail.explanation.score_breakdown.experience,
                location=detail.explanation.score_breakdown.location,
                contract=detail.explanation.score_breakdown.contract,
                daily_rate=detail.explanation.score_breakdown.daily_rate,
            ),
            matching_reasons=list(detail.explanation.matching_reasons),
            warnings=list(detail.explanation.warnings),
            strong_points=list(detail.explanation.strong_points),
            missing_skills=list(detail.explanation.missing_skills),
            recommendations=list(detail.explanation.recommendations),
        ),
    )


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    user_profile_id: UUID = Depends(get_current_user_profile_id),
    use_case: GetDashboardSummary = Depends(get_dashboard_summary_use_case),
) -> DashboardSummaryResponse:
    """Returns aggregate statistics for the user's dashboard header card."""
    try:
        summary = await use_case.execute(user_profile_id)
    except DatabaseError:
        raise HTTPException(status_code=500, detail="Database error")

    return DashboardSummaryResponse(
        kpis=DashboardKpisResponse(
            total_missions=summary.kpis.total_missions,
            new_today=summary.kpis.new_today,
            average_score=summary.kpis.average_score,
            last_refresh=summary.kpis.last_refresh,
            pipeline_status=summary.kpis.pipeline_status,
        ),
        health=PipelineHealthResponse(
            status=summary.health.status,
            last_pipeline_duration_seconds=summary.health.last_pipeline_duration_seconds,
        ),
    )
