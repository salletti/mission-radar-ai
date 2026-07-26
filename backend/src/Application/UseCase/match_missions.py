from src.Application.DTO.match_mission_result import MatchMissionResult
from src.Application.Exception.application_error import ProfileEmbeddingMissingError
from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.search_query_raw_post_repository import SearchQueryRawPostRepository
from src.Domain.Repository.search_query_repository import SearchQueryRepository
from src.Domain.Service.mission_match_scorer import MissionMatchScorer


class MatchMissions:
    """Scores analyzed missions against a user profile and persists the results.

    Resolves the user-scoped mission set via SearchQuery → SearchQueryRawPost → AnalyzedPost,
    delegates all score computation to MissionMatchScorer, persists every scored MissionMatch,
    then filters by min_score and returns the top-N results sorted by final_score descending.
    """

    def __init__(
        self,
        scorer: MissionMatchScorer,
        search_query_repository: SearchQueryRepository,
        search_query_raw_post_repository: SearchQueryRawPostRepository,
        analyzed_post_repository: AnalyzedPostRepository,
        mission_match_repository: MissionMatchRepository,
        min_score: float = 0.50,
        top_n: int = 20,
    ) -> None:
        self._scorer = scorer
        self._search_query_repository = search_query_repository
        self._search_query_raw_post_repository = search_query_raw_post_repository
        self._analyzed_post_repository = analyzed_post_repository
        self._mission_match_repository = mission_match_repository
        self._min_score = min_score
        self._top_n = top_n

    async def execute(self, profile: UserProfile) -> list[MatchMissionResult]:
        if profile.embedding is None:
            raise ProfileEmbeddingMissingError(
                "UserProfile has no embedding — run SaveProfile first"
            )

        queries = await self._search_query_repository.get_by_profile(profile.id)
        if not queries:
            return []

        query_ids = [q.id for q in queries]
        links = await self._search_query_raw_post_repository.find_by_search_query_ids(query_ids)
        if not links:
            return []

        raw_post_ids = list({lnk.raw_post_id for lnk in links})

        missions = await self._analyzed_post_repository.find_by_raw_post_ids(raw_post_ids)
        if not missions:
            return []

        results: list[MatchMissionResult] = []
        for mission in missions:
            if mission.embedding is None:
                continue
            match_score = await self._scorer.calculate(profile, mission)
            results.append(MatchMissionResult(mission=mission, match_score=match_score))

        await self._mission_match_repository.delete_user_matches(profile.id)
        mission_matches = [
            MissionMatch.create(
                user_profile_id=profile.id,
                analyzed_post_id=result.mission.id,
                match_score=result.match_score,
            )
            for result in results
        ]
        await self._mission_match_repository.save_many(mission_matches)

        filtered = [r for r in results if r.match_score.final_score >= self._min_score]
        return sorted(
            filtered, key=lambda r: r.match_score.final_score, reverse=True
        )[: self._top_n]
