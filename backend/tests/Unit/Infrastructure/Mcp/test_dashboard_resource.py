"""Unit tests for DashboardResource — no I/O, no DB, no real MCP server. Fakes only."""
from typing import Optional
from uuid import UUID, uuid4

import pytest

from src.Application.UseCase.get_dashboard_summary import GetDashboardSummary
from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.Entity.pipeline_run import PipelineRun
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.pipeline_run_repository import PipelineRunRepository
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver
from src.Infrastructure.Mcp.Resource.dashboard_resource import DashboardResource


class FakeMissionMatchRepository(MissionMatchRepository):
    def __init__(self, matches: Optional[list[MissionMatch]] = None) -> None:
        self._matches = matches or []

    async def get_by_user(self, user_id: UUID) -> list[MissionMatch]:
        return [m for m in self._matches if m.user_profile_id == user_id]

    async def save(self, match: MissionMatch) -> None: ...
    async def save_many(self, matches: list[MissionMatch]) -> None: ...
    async def get_by_id(self, match_id: UUID) -> Optional[MissionMatch]: return None
    async def get_by_post(self, post_id: UUID) -> list[MissionMatch]: return []
    async def get_best_matches(self, user_id: UUID, limit: int) -> list[MissionMatch]: return []
    async def delete_user_matches(self, user_id: UUID) -> None: ...


class FakePipelineRunRepository(PipelineRunRepository):
    def __init__(self, latest: Optional[PipelineRun] = None) -> None:
        self._latest = latest

    async def find_latest_for_user(self, user_id: UUID) -> Optional[PipelineRun]:
        return self._latest

    async def save(self, run: PipelineRun) -> None: ...
    async def get_by_id(self, run_id: UUID) -> Optional[PipelineRun]: return None
    async def find_running_for_user(self, user_id: UUID) -> Optional[PipelineRun]: return None
    async def update(self, run: PipelineRun) -> None: ...


class FakeIdentityResolver(IdentityResolver):
    def __init__(self, user_profile_id: UUID) -> None:
        self._user_profile_id = user_profile_id

    async def resolve(self) -> UUID:
        return self._user_profile_id


@pytest.mark.asyncio
async def test_dashboard_resource_returns_structured_summary() -> None:
    user_id = uuid4()
    get_dashboard_summary = GetDashboardSummary(
        mission_match_repository=FakeMissionMatchRepository([]),
        pipeline_run_repository=FakePipelineRunRepository(None),
    )
    resource = DashboardResource(
        identity_resolver=FakeIdentityResolver(user_id), get_dashboard_summary=get_dashboard_summary
    )

    payload = await resource.execute()

    assert payload == {
        "kpis": {
            "total_missions": 0,
            "new_today": 0,
            "average_score": 0,
            "last_refresh": None,
            "pipeline_status": None,
        },
        "health": {"status": "UNKNOWN", "last_pipeline_duration_seconds": None},
    }
