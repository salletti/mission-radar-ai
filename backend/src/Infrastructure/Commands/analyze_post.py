import argparse
import asyncio
import sys
from uuid import UUID

from src.Application.DTO.analyze_raw_post_result import AnalyzeRawPostResult
from src.Application.UseCase.analyze_raw_post import AnalyzeRawPost
from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.raw_post import RawPost
from src.Domain.Service.mission_embedding_builder import MissionEmbeddingBuilder
from src.Domain.Service.mission_normalizer import MissionNormalizer
from src.Infrastructure.Config.database import AsyncSessionLocal
from src.Infrastructure.Config.settings import settings
from src.Infrastructure.External.Embedding.sentence_transformer_embedding_gateway import SentenceTransformerEmbeddingGateway
from src.Infrastructure.External.LLM.groq_llm_gateway import GroqLLMGateway
from src.Infrastructure.External.Observability.langfuse.factory import get_langfuse_tracer
from src.Infrastructure.Persistence.Repository.analyzed_post_repository import SqlAlchemyAnalyzedPostRepository
from src.Infrastructure.Persistence.Repository.raw_post_repository import SqlAlchemyRawPostRepository

_CONTENT_PREVIEW_LENGTH = 120


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze a RawPost via Groq LLM and save to DB")
    parser.add_argument("--post-id", required=True, help="UUID of the RawPost to analyze")
    return parser.parse_args(argv)


def _print_result(
    raw_post: RawPost,
    result: AnalyzeRawPostResult,
    analyzed_post: AnalyzedPost | None,
) -> None:
    preview = raw_post.content[:_CONTENT_PREVIEW_LENGTH].replace("\n", " ")
    if len(raw_post.content) > _CONTENT_PREVIEW_LENGTH:
        preview += "…"

    print("=" * 50)
    print("MISSION RADAR AI — Analyze Post")
    print("=" * 50)
    print(f"\nPost    : {raw_post.author_name} ({raw_post.published_at.date()})")
    print(f"URL     : {raw_post.post_url}")
    print(f"Contenu : {preview}")
    print(f"\n--- Statut : {result.status.upper()} ---")

    if result.status == "skipped":
        print("Non une offre d'emploi — ignoré (aucune sauvegarde)")
        print("=" * 50)
        return

    if analyzed_post is None:
        print("=" * 50)
        return

    print(f"analyzed_post_id : {analyzed_post.id}")
    print(f"\ntitle            : {analyzed_post.title or '—'}")
    print(f"company          : {analyzed_post.company or '—'}")
    print(f"location         : {analyzed_post.location or '—'}")
    print(f"seniority        : {analyzed_post.seniority or '—'}")
    print(f"contract_type    : {analyzed_post.detected_contract_type.value}")
    print(f"remote_mode      : {analyzed_post.detected_remote_mode.value}")
    print(f"detected_tjm     : {analyzed_post.detected_tjm or '—'}")
    print(f"detected_stack   : {', '.join(analyzed_post.detected_stack) or '—'}")
    print(f"summary          : {analyzed_post.summary}")
    embedding_dims = len(analyzed_post.embedding) if analyzed_post.embedding else 0
    print(f"embedding        : {embedding_dims} dims")
    print("=" * 50)


async def _run(post_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        raw_post_repo = SqlAlchemyRawPostRepository(session)
        analyzed_post_repo = SqlAlchemyAnalyzedPostRepository(session)

        raw_post = await raw_post_repo.get_by_id(post_id)
        if raw_post is None:
            print(f"RawPost {post_id} not found", file=sys.stderr)
            sys.exit(1)

        use_case = AnalyzeRawPost(
            llm=GroqLLMGateway(api_key=settings.GROQ_API_KEY, tracer=get_langfuse_tracer()),
            mission_normalizer=MissionNormalizer(),
            mission_embedding_builder=MissionEmbeddingBuilder(),
            embedding_gateway=SentenceTransformerEmbeddingGateway(),
            analyzed_post_repository=analyzed_post_repo,
        )
        result = await use_case.execute(raw_post)
        await session.commit()

        analyzed_post = (
            await analyzed_post_repo.get_by_id(result.analyzed_post_id)
            if result.analyzed_post_id
            else None
        )

    _print_result(raw_post, result, analyzed_post)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        post_id = UUID(args.post_id)
    except ValueError:
        print(f"Invalid UUID: {args.post_id}", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(_run(post_id))
    except Exception as e:
        print(f"Error while analyzing post:\n{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
