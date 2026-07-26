from src.Domain.Entity.search_query_raw_post import SearchQueryRawPost
from src.Infrastructure.Persistence.SQLAlchemy.Models.search_query_raw_post_model import SearchQueryRawPostModel


class SearchQueryRawPostMapper:
    @staticmethod
    def to_domain(model: SearchQueryRawPostModel) -> SearchQueryRawPost:
        return SearchQueryRawPost(
            id=model.id,
            search_query_id=model.search_query_id,
            raw_post_id=model.raw_post_id,
            created_at=model.created_at,
        )

    @staticmethod
    def to_model(entity: SearchQueryRawPost) -> SearchQueryRawPostModel:
        return SearchQueryRawPostModel(
            id=entity.id,
            search_query_id=entity.search_query_id,
            raw_post_id=entity.raw_post_id,
            created_at=entity.created_at,
        )
