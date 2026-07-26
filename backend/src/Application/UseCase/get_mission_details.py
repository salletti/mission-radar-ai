from src.Application.DTO.explainability_report import ExplainabilityReport, ScoreBreakdown
from src.Application.DTO.get_mission_details_query import GetMissionDetailsQuery
from src.Application.DTO.mission_match_detail import MissionMatchDetail
from src.Application.Exception.application_error import UserProfileNotFoundError
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Exception.domain_exceptions import MissionMatchNotFoundError
from src.Domain.Repository.analyzed_post_repository import AnalyzedPostRepository
from src.Domain.Repository.mission_match_repository import MissionMatchRepository
from src.Domain.Repository.raw_post_repository import RawPostRepository
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Domain.ValueObject.match_score import MatchScore


class GetMissionDetails:
    """Returns the full detail of a single MissionMatch, verified against the requesting user."""

    def __init__(
        self,
        mission_match_repository: MissionMatchRepository,
        analyzed_post_repository: AnalyzedPostRepository,
        raw_post_repository: RawPostRepository,
        user_profile_repository: UserProfileRepository,
    ) -> None:
        self._mission_match_repository = mission_match_repository
        self._analyzed_post_repository = analyzed_post_repository
        self._raw_post_repository = raw_post_repository
        self._user_profile_repository = user_profile_repository

    async def execute(self, query: GetMissionDetailsQuery) -> MissionMatchDetail:
        match = await self._mission_match_repository.get_by_id(query.mission_match_id)
        if match is None or match.user_profile_id != query.user_profile_id:
            raise MissionMatchNotFoundError(
                f"MissionMatch {query.mission_match_id} not found"
            )

        analyzed = await self._analyzed_post_repository.get_by_id(match.analyzed_post_id)
        if analyzed is None:
            raise MissionMatchNotFoundError(
                f"AnalyzedPost {match.analyzed_post_id} not found"
            )

        raw = await self._raw_post_repository.get_by_id(analyzed.raw_post_id)
        if raw is None:
            raise MissionMatchNotFoundError(
                f"RawPost {analyzed.raw_post_id} not found"
            )

        user = await self._user_profile_repository.get_by_id(query.user_profile_id)
        if user is None:
            raise UserProfileNotFoundError(
                f"UserProfile {query.user_profile_id} not found"
            )

        user_skills = set(user.skills.technologies)
        matched_skills = tuple(s for s in analyzed.detected_stack if s in user_skills)
        missing_skills = tuple(s for s in analyzed.detected_stack if s not in user_skills)
        explanation = self._build_explanation(user, analyzed, match.match_score, matched_skills, missing_skills)

        return MissionMatchDetail(
            mission_match_id=match.id,
            analyzed_post_id=analyzed.id,
            raw_post_id=raw.id,
            author_name=raw.author_name,
            author_url=raw.author_url,
            content=raw.content,
            post_url=raw.post_url,
            published_at=raw.published_at,
            title=analyzed.title,
            company=analyzed.company,
            location=analyzed.location,
            summary=analyzed.summary,
            seniority=analyzed.seniority,
            detected_stack=analyzed.detected_stack,
            detected_contract_type=analyzed.detected_contract_type.value,
            detected_remote_mode=analyzed.detected_remote_mode.value,
            detected_tjm=analyzed.detected_tjm,
            global_score=match.final_score,
            score_details={
                "semantic": match.match_score.semantic_score,
                "contract": match.match_score.contract_score,
                "tjm": match.match_score.tjm_score,
                "remote": match.match_score.remote_score,
            },
            matched_at=match.created_at,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            explanation=explanation,
        )

    @staticmethod
    def _build_explanation(
        user: UserProfile,
        analyzed: AnalyzedPost,
        score: MatchScore,
        matched_skills: tuple[str, ...],
        missing_skills: tuple[str, ...],
    ) -> ExplainabilityReport:
        matching_reasons: list[str] = []
        for skill in matched_skills[:3]:
            matching_reasons.append(f"Votre expérience {skill} correspond à la stack demandée.")
        if score.contract_score >= 0.9:
            label = user.preferred_contract_type.value.replace("_", " ")
            matching_reasons.append(
                f"Votre préférence de contrat ({label}) correspond au type proposé."
            )
        if score.remote_score >= 0.9:
            label = user.preferred_remote_mode.value.replace("_", " ")
            matching_reasons.append(
                f"Votre préférence de télétravail ({label}) correspond aux modalités proposées."
            )
        if score.tjm_score >= 0.7 and analyzed.detected_tjm:
            matching_reasons.append(
                f"Votre TJM cible est compatible avec le TJM détecté ({analyzed.detected_tjm:.0f}€/j)."
            )

        return ExplainabilityReport(
            score_breakdown=ScoreBreakdown(
                contract=score.contract_score,
                daily_rate=score.tjm_score,
            ),
            matching_reasons=tuple(matching_reasons),
            warnings=(),
            strong_points=matched_skills,
            missing_skills=missing_skills,
            recommendations=(),
        )
