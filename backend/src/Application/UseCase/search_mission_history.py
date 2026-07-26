from typing import Optional
from uuid import UUID

from src.Application.DTO.search_mission_history_query import SearchMissionHistoryQuery
from src.Application.DTO.today_mission import TodayMission
from src.Application.UseCase.today_mission_assembler import TodayMissionAssembler
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.raw_post_repository import RawPostRepository


class SearchMissionHistory:
    """Searches a user's full mission match history by keyword against title, company,
    and detected stack. Distinct from GetMissionHistory (plain chronological browsing)
    because it answers a different business question and is expected to grow independent
    search criteria (company, stack, remote, TJM, semantic search) over time without
    destabilizing GetMissionHistory's contract, which the dashboard REST endpoint relies on.
    """

    def __init__(
        self,
        mission_match_repository: MissionMatchRepository,
        analyzed_post_repository: AnalyzedPostRepository,
        raw_post_repository: RawPostRepository,
    ) -> None:
        self._mission_match_repository = mission_match_repository
        self._analyzed_post_repository = analyzed_post_repository
        self._assembler = TodayMissionAssembler(analyzed_post_repository, raw_post_repository)

    async def execute(self, query: SearchMissionHistoryQuery) -> list[TodayMission]:
        matches = await self._mission_match_repository.get_by_user(query.user_profile_id)
        score_filtered = [m for m in matches if m.final_score >= query.min_score]

        if query.keyword:
            score_filtered = await self._filter_by_keyword(score_filtered, query.keyword)

        paginated = sorted(score_filtered, key=lambda m: m.created_at, reverse=True)[
            query.offset : query.offset + query.limit
        ]

        return await self._assembler.assemble(paginated)

    async def _filter_by_keyword(self, matches: list[MissionMatch], keyword: str) -> list[MissionMatch]:
        if not matches:
            return []

        analyzed_post_ids = [m.analyzed_post_id for m in matches]
        analyzed_posts = await self._analyzed_post_repository.find_by_ids(analyzed_post_ids)
        analyzed_map: dict[UUID, AnalyzedPost] = {ap.id: ap for ap in analyzed_posts}

        needle = keyword.lower()
        return [m for m in matches if self._matches_keyword(analyzed_map.get(m.analyzed_post_id), needle)]

    @staticmethod
    def _matches_keyword(analyzed: Optional[AnalyzedPost], needle: str) -> bool:
        if analyzed is None:
            return False
        if analyzed.title and needle in analyzed.title.lower():
            return True
        if analyzed.company and needle in analyzed.company.lower():
            return True
        return any(needle in tech.lower() for tech in analyzed.detected_stack)
