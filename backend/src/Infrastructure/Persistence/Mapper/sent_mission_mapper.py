from src.Domain.Entity.sent_mission import SentMission
from src.Infrastructure.Persistence.SQLAlchemy.Models.sent_mission_model import SentMissionModel


class SentMissionMapper:
    @staticmethod
    def to_domain(model: SentMissionModel) -> SentMission:
        return SentMission(
            id=model.id,
            user_profile_id=model.user_profile_id,
            analyzed_post_id=model.analyzed_post_id,
            sent_at=model.sent_at,
        )

    @staticmethod
    def to_model(entity: SentMission) -> SentMissionModel:
        return SentMissionModel(
            id=entity.id,
            user_profile_id=entity.user_profile_id,
            analyzed_post_id=entity.analyzed_post_id,
            sent_at=entity.sent_at,
        )
