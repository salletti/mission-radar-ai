from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Infrastructure.Persistence.SQLAlchemy.Models.analyzed_post_model import AnalyzedPostModel


class AnalyzedPostMapper:
    @staticmethod
    def to_domain(model: AnalyzedPostModel) -> AnalyzedPost:
        return AnalyzedPost(
            id=model.id,
            raw_post_id=model.raw_post_id,
            summary=model.summary,
            detected_stack=tuple(model.detected_stack or []),
            detected_tjm=model.detected_tjm_amount,
            detected_contract_type=ContractType(model.detected_contract_type),
            detected_remote_mode=RemoteMode(model.detected_remote_mode),
            title=model.title,
            company=model.company,
            location=model.location,
            seniority=model.seniority,
            embedding=model.embedding,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: AnalyzedPost) -> AnalyzedPostModel:
        return AnalyzedPostModel(
            id=entity.id,
            raw_post_id=entity.raw_post_id,
            summary=entity.summary,
            detected_stack=list(entity.detected_stack),
            detected_tjm_amount=entity.detected_tjm,
            detected_contract_type=entity.detected_contract_type.value,
            detected_remote_mode=entity.detected_remote_mode.value,
            title=entity.title,
            company=entity.company,
            location=entity.location,
            seniority=entity.seniority,
            embedding=entity.embedding,
            created_at=entity.created_at,
        )
