from src.Domain.Entity.user_profile import UserProfile
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack
from src.Infrastructure.Persistence.SQLAlchemy.Models.user_profile_model import UserProfileModel


class UserProfileMapper:
    @staticmethod
    def to_domain(model: UserProfileModel) -> UserProfile:
        return UserProfile(
            id=model.id,
            email=model.email,
            full_name=model.full_name,
            title=model.title,
            years_experience=model.years_experience,
            preferred_contract_type=ContractType(model.preferred_contract_type),
            target_tjm=model.target_tjm,
            preferred_remote_mode=RemoteMode(model.preferred_remote_mode),
            location=model.location,
            availability=model.availability,
            skills=Stack.from_list(model.skills),
            embedding=[float(v) for v in model.embedding] if model.embedding is not None else None,
            cv_raw_text=model.cv_raw_text,
        )

    @staticmethod
    def to_model(entity: UserProfile) -> UserProfileModel:
        return UserProfileModel(
            id=entity.id,
            email=entity.email,
            full_name=entity.full_name,
            title=entity.title,
            years_experience=entity.years_experience,
            preferred_contract_type=entity.preferred_contract_type.value,
            target_tjm=entity.target_tjm,
            preferred_remote_mode=entity.preferred_remote_mode.value,
            location=entity.location,
            availability=entity.availability,
            skills=list(entity.skills.technologies),
            embedding=entity.embedding,
            cv_raw_text=entity.cv_raw_text,
        )
