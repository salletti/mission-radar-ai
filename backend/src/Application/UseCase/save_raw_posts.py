from dataclasses import dataclass
from uuid import UUID

from src.Domain.Entity.raw_post import RawPost
from src.Domain.Entity.search_query_raw_post import SearchQueryRawPost
from src.Domain.Repository.raw_post_repository import RawPostRepository
from src.Domain.Repository.search_query_raw_post_repository import SearchQueryRawPostRepository


@dataclass(frozen=True)
class SaveRawPostsResult:
    """Résultat de la persistance d'un batch de posts."""

    total: int
    saved: int
    skipped: int
    links_created: int
    new_post_ids: tuple[UUID, ...]
    all_post_ids: tuple[UUID, ...]


class SaveRawPosts:
    """Persiste une liste de RawPost et leurs liaisons SearchQuery → RawPost.

    Un post existant (doublon) génère quand même une liaison si elle n'existe pas encore :
    une même query peut retrouver un post déjà collecté par une autre query.
    """

    def __init__(
        self,
        repository: RawPostRepository,
        link_repository: SearchQueryRawPostRepository,
    ) -> None:
        self._repository = repository
        self._link_repository = link_repository

    async def execute(self, posts: list[RawPost], search_query_id: UUID) -> SaveRawPostsResult:
        new_posts: list[RawPost] = []
        existing_post_ids: list[UUID] = []

        for post in posts:
            existing = await self._repository.get_by_source_and_external_id(post.source, post.external_id)
            if existing is not None:
                existing_post_ids.append(existing.id)
            else:
                new_posts.append(post)

        await self._repository.save_many(new_posts)

        all_post_ids = tuple(post.id for post in new_posts) + tuple(existing_post_ids)

        links_created = 0
        for raw_post_id in all_post_ids:
            if not await self._link_repository.exists(search_query_id, raw_post_id):
                await self._link_repository.save(
                    SearchQueryRawPost(search_query_id=search_query_id, raw_post_id=raw_post_id)
                )
                links_created += 1

        new_post_ids = tuple(post.id for post in new_posts)
        return SaveRawPostsResult(
            total=len(posts),
            saved=len(new_posts),
            skipped=len(existing_post_ids),
            links_created=links_created,
            new_post_ids=new_post_ids,
            all_post_ids=all_post_ids,
        )
