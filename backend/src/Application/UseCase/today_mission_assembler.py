from uuid import UUID

from src.Application.DTO.today_mission import TodayMission
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.Entity.raw_post import RawPost
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.raw_post_repository import RawPostRepository

_EXCERPT_LENGTH = 300


class TodayMissionAssembler:
    """Assembles TodayMission DTOs from MissionMatch entities by batch-fetching their
    related AnalyzedPost/RawPost data (N+1-free). Shared by every read Use Case that
    returns list[TodayMission] (GetTodayMissions, GetMissionHistory, SearchMissionHistory)
    to avoid tripling this fetch-and-build logic."""

    def __init__(
        self,
        analyzed_post_repository: AnalyzedPostRepository,
        raw_post_repository: RawPostRepository,
    ) -> None:
        self._analyzed_post_repository = analyzed_post_repository
        self._raw_post_repository = raw_post_repository

    async def assemble(self, matches: list[MissionMatch]) -> list[TodayMission]:
        if not matches:
            return []

        analyzed_post_ids = [m.analyzed_post_id for m in matches]
        analyzed_posts = await self._analyzed_post_repository.find_by_ids(analyzed_post_ids)
        analyzed_map: dict[UUID, AnalyzedPost] = {ap.id: ap for ap in analyzed_posts}

        raw_post_ids = [ap.raw_post_id for ap in analyzed_posts]
        raw_posts = await self._raw_post_repository.find_by_ids(raw_post_ids)
        raw_map: dict[UUID, RawPost] = {rp.id: rp for rp in raw_posts}

        results: list[TodayMission] = []
        for match in matches:
            analyzed = analyzed_map.get(match.analyzed_post_id)
            if analyzed is None:
                continue
            raw = raw_map.get(analyzed.raw_post_id)
            if raw is None:
                continue

            results.append(
                TodayMission(
                    mission_match_id=match.id,
                    analyzed_post_id=analyzed.id,
                    raw_post_id=raw.id,
                    author_name=raw.author_name,
                    content_excerpt=raw.content[:_EXCERPT_LENGTH],
                    post_url=raw.post_url,
                    detected_stack=analyzed.detected_stack,
                    detected_contract_type=analyzed.detected_contract_type.value,
                    detected_remote_mode=analyzed.detected_remote_mode.value,
                    global_score=match.final_score,
                    score_details={
                        "semantic": match.match_score.semantic_score,
                        "contract": match.match_score.contract_score,
                        "tjm": match.match_score.tjm_score,
                        "remote": match.match_score.remote_score,
                    },
                    detected_tjm=analyzed.detected_tjm,
                    title=analyzed.title,
                    company=analyzed.company,
                    location=analyzed.location,
                )
            )

        return results
