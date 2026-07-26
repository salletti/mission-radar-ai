from src.Domain.Entity.mission_match import MissionMatch
from src.Domain.ValueObject.match_score import MatchScore
from src.Infrastructure.Persistence.SQLAlchemy.Models.mission_match_model import MissionMatchModel


class MissionMatchMapper:
    @staticmethod
    def to_domain(model: MissionMatchModel) -> MissionMatch:
        score = MatchScore(
            semantic_score=model.semantic_score,
            contract_score=model.contract_score,
            remote_score=model.remote_score,
            tjm_score=model.tjm_score,
        )
        return MissionMatch(
            id=model.id,
            user_profile_id=model.user_profile_id,
            analyzed_post_id=model.analyzed_post_id,
            match_score=score,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: MissionMatch) -> MissionMatchModel:
        return MissionMatchModel(
            id=entity.id,
            user_profile_id=entity.user_profile_id,
            analyzed_post_id=entity.analyzed_post_id,
            semantic_score=entity.match_score.semantic_score,
            stack_score=0.0,
            contract_score=entity.match_score.contract_score,
            tjm_score=entity.match_score.tjm_score,
            remote_score=entity.match_score.remote_score,
            global_score=entity.final_score,
            created_at=entity.created_at,
            updated_at=entity.created_at,
        )
