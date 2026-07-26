from src.Domain.Entity.search_query import SearchQuery
from src.Infrastructure.Persistence.SQLAlchemy.Models.search_query_model import SearchQueryModel


class SearchQueryMapper:
    @staticmethod
    def to_domain(model: SearchQueryModel) -> SearchQuery:
        return SearchQuery(
            id=model.id,
            user_profile_id=model.user_profile_id,
            query=model.query,
            source=model.source,
            limit=model.limit,
        )

    @staticmethod
    def to_model(entity: SearchQuery) -> SearchQueryModel:
        return SearchQueryModel(
            id=entity.id,
            user_profile_id=entity.user_profile_id,
            query=entity.query,
            source=entity.source,
            limit=entity.limit,
        )
