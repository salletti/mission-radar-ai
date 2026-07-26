from src.Domain.Entity.raw_post import RawPost
from src.Infrastructure.Persistence.SQLAlchemy.Models.raw_post_model import RawPostModel


class RawPostMapper:
    @staticmethod
    def to_domain(model: RawPostModel) -> RawPost:
        return RawPost(
            id=model.id,
            source=model.source,
            external_id=model.external_id,
            author_name=model.author_name,
            author_url=model.author_url,
            content=model.content,
            post_url=model.post_url,
            published_at=model.published_at,
            scraped_at=model.scraped_at,
        )

    @staticmethod
    def to_model(entity: RawPost) -> RawPostModel:
        return RawPostModel(
            id=entity.id,
            source=entity.source,
            external_id=entity.external_id,
            author_name=entity.author_name,
            author_url=entity.author_url,
            content=entity.content,
            post_url=entity.post_url,
            published_at=entity.published_at,
            scraped_at=entity.scraped_at,
        )
