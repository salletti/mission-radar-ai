from src.Application.Gateway.embedding_gateway import EmbeddingGateway
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.match_score import MatchScore
from src.Domain.ValueObject.remote_mode import RemoteMode

# Beyond this € gap the TJM score reaches 0.0
_TJM_TOLERANCE = 200.0


class MissionMatchScorer:
    """Domain service computing a MatchScore from a UserProfile and AnalyzedPost.

    V1 formula: semantic 70%, contract 15%, remote 10%, TJM 5%.
    Unknown fields (None / UNKNOWN enum) return a neutral 0.5 so they
    neither penalise nor reward the global score.
    """

    def __init__(self, embedding_gateway: EmbeddingGateway) -> None:
        self._embedding = embedding_gateway

    async def calculate(self, profile: UserProfile, mission: AnalyzedPost) -> MatchScore:
        return MatchScore(
            semantic_score=await self._semantic_score(profile, mission),
            contract_score=self._contract_score(profile, mission),
            remote_score=self._remote_score(profile, mission),
            tjm_score=self._tjm_score(profile, mission),
        )

    async def _semantic_score(self, profile: UserProfile, mission: AnalyzedPost) -> float:
        if profile.embedding is None or mission.embedding is None:
            return 0.0
        return await self._embedding.compute_similarity(profile.embedding, mission.embedding)

    def _contract_score(self, profile: UserProfile, mission: AnalyzedPost) -> float:
        if mission.detected_contract_type == ContractType.UNKNOWN:
            return 0.5
        return 1.0 if profile.preferred_contract_type == mission.detected_contract_type else 0.0

    def _remote_score(self, profile: UserProfile, mission: AnalyzedPost) -> float:
        if mission.detected_remote_mode == RemoteMode.UNKNOWN:
            return 0.5
        return 1.0 if profile.preferred_remote_mode == mission.detected_remote_mode else 0.0

    def _tjm_score(self, profile: UserProfile, mission: AnalyzedPost) -> float:
        if mission.detected_tjm is None:
            return 0.5
        diff = abs(mission.detected_tjm - profile.target_tjm)
        return max(0.0, 1.0 - diff / _TJM_TOLERANCE)
