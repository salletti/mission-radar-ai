from src.Domain.Entity.digest_history import DigestHistory, DigestStatus
from src.Infrastructure.Persistence.SQLAlchemy.Models.digest_history_model import DigestHistoryModel


class DigestHistoryMapper:
    @staticmethod
    def to_domain(model: DigestHistoryModel) -> DigestHistory:
        return DigestHistory(
            id=model.id,
            user_id=model.user_id,
            pipeline_run_id=model.pipeline_run_id,
            sent_at=model.sent_at,
            status=DigestStatus(model.status),
            missions_count=model.missions_count,
            provider_message_id=model.provider_message_id,
            error_message=model.error_message,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: DigestHistory) -> DigestHistoryModel:
        return DigestHistoryModel(
            id=entity.id,
            user_id=entity.user_id,
            pipeline_run_id=entity.pipeline_run_id,
            sent_at=entity.sent_at,
            status=entity.status.value,
            missions_count=entity.missions_count,
            provider_message_id=entity.provider_message_id,
            error_message=entity.error_message,
            created_at=entity.created_at,
        )
