from src.Application.DTO.get_today_missions_query import GetTodayMissionsQuery
from src.Application.DTO.today_mission import TodayMission
from src.Application.UseCase.today_mission_assembler import TodayMissionAssembler
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.raw_post_repository import RawPostRepository


class GetTodayMissions:
    """Returns the top-scored missions for a user, enriched with post details."""

    def __init__(
        self,
        mission_match_repository: MissionMatchRepository,
        analyzed_post_repository: AnalyzedPostRepository,
        raw_post_repository: RawPostRepository,
    ) -> None:
        self._mission_match_repository = mission_match_repository
        self._assembler = TodayMissionAssembler(analyzed_post_repository, raw_post_repository)

    async def execute(self, query: GetTodayMissionsQuery) -> list[TodayMission]:
        matches = await self._mission_match_repository.get_by_user(query.user_profile_id)

        filtered = sorted(
            [m for m in matches if m.final_score >= query.min_score],
            key=lambda m: m.final_score,
            reverse=True,
        )[: query.limit]

        return await self._assembler.assemble(filtered)
