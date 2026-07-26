from src.Domain.Entity.external_identity import ExternalIdentity
from src.Infrastructure.Persistence.SQLAlchemy.Models.external_identity_model import ExternalIdentityModel


class ExternalIdentityMapper:
    @staticmethod
    def to_domain(model: ExternalIdentityModel) -> ExternalIdentity:
        return ExternalIdentity(
            id=model.id,
            user_profile_id=model.user_profile_id,
            provider=model.provider,
            subject=model.subject,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: ExternalIdentity) -> ExternalIdentityModel:
        return ExternalIdentityModel(
            id=entity.id,
            user_profile_id=entity.user_profile_id,
            provider=entity.provider,
            subject=entity.subject,
            created_at=entity.created_at,
        )
