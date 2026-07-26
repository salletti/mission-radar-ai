import argparse
import asyncio
import sys
from uuid import UUID

from src.Application.Exception.application_error import ProfileEmbeddingMissingError
from src.Application.UseCase.match_missions import MatchMissions
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Service.mission_match_scorer import MissionMatchScorer
from src.Infrastructure.Config.database import AsyncSessionLocal
from src.Infrastructure.External.Embedding.sentence_transformer_embedding_gateway import (
    SentenceTransformerEmbeddingGateway,
)
from src.Infrastructure.Persistence.Repository.analyzed_post_repository import (
    SqlAlchemyAnalyzedPostRepository,
)
from src.Infrastructure.Persistence.Repository.mission_match_repository import (
    SqlAlchemyMissionMatchRepository,
)
from src.Infrastructure.Persistence.Repository.search_query_raw_post_repository import (
    SqlAlchemySearchQueryRawPostRepository,
)
from src.Infrastructure.Persistence.Repository.search_query_repository import (
    SqlAlchemySearchQueryRepository,
)
from src.Infrastructure.Persistence.Repository.user_profile_repository import (
    SqlAlchemyUserProfileRepository,
)

_SUMMARY_PREVIEW_LENGTH = 120
_SKILLS_PREVIEW = 8


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Match missions for a user profile using semantic + business scoring"
    )
    parser.add_argument("--profile-id", required=True, help="UUID of the UserProfile")
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.50,
        help="Minimum score threshold (default: 0.50)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=20,
        help="Maximum number of results to display (default: 20)",
    )
    return parser.parse_args(argv)


def _print_results(results: list, profile: UserProfile) -> None:
    skills_preview = ", ".join(profile.skills.technologies[:_SKILLS_PREVIEW])
    if len(profile.skills.technologies) > _SKILLS_PREVIEW:
        skills_preview += ", …"

    print("=" * 60)
    print("MISSION RADAR AI — Match Missions")
    print("=" * 60)
    print(f"\nProfile : {profile.full_name} <{profile.email}>")
    print(f"Title   : {profile.title}")
    print(f"Skills  : {skills_preview or '—'}")
    print(f"\nTop {len(results)} match(es) found\n")

    for i, result in enumerate(results, start=1):
        mission = result.mission
        score = result.match_score
        summary_preview = mission.summary[:_SUMMARY_PREVIEW_LENGTH].replace("\n", " ")
        if len(mission.summary) > _SUMMARY_PREVIEW_LENGTH:
            summary_preview += "…"

        print("-" * 60)
        print(f"\n[{i}] Score : {score.final_score:.3f}\n")
        print(f"  id            : {mission.id}")
        print(f"  title         : {mission.title or '—'}")
        print(f"  company       : {mission.company or '—'}")
        print(f"  contract_type : {mission.detected_contract_type.value}")
        print(f"  remote_mode   : {mission.detected_remote_mode.value}")
        print(f"  detected_tjm  : {mission.detected_tjm or '—'}")
        print(f"  stack         : {', '.join(mission.detected_stack) or '—'}")
        print(f"  summary       : {summary_preview}")
        print(
            f"\n  scores        : semantic={score.semantic_score:.3f}"
            f"  contract={score.contract_score:.3f}"
            f"  remote={score.remote_score:.3f}"
            f"  tjm={score.tjm_score:.3f}"
        )

    print("-" * 60)


async def _run(profile_id: UUID, min_score: float, top_n: int) -> None:
    async with AsyncSessionLocal() as session:
        profile_repo = SqlAlchemyUserProfileRepository(session)
        search_query_repo = SqlAlchemySearchQueryRepository(session)
        search_query_raw_post_repo = SqlAlchemySearchQueryRawPostRepository(session)
        analyzed_post_repo = SqlAlchemyAnalyzedPostRepository(session)

        profile = await profile_repo.get_by_id(profile_id)
        if profile is None:
            print(f"UserProfile {profile_id} not found", file=sys.stderr)
            sys.exit(1)

        mission_match_repo = SqlAlchemyMissionMatchRepository(session)
        scorer = MissionMatchScorer(SentenceTransformerEmbeddingGateway())
        use_case = MatchMissions(
            scorer=scorer,
            search_query_repository=search_query_repo,
            search_query_raw_post_repository=search_query_raw_post_repo,
            analyzed_post_repository=analyzed_post_repo,
            mission_match_repository=mission_match_repo,
            min_score=min_score,
            top_n=top_n,
        )
        results = await use_case.execute(profile)

    _print_results(results, profile)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        profile_id = UUID(args.profile_id)
    except ValueError:
        print(f"Invalid UUID: {args.profile_id}", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(_run(profile_id, args.min_score, args.top_n))
    except ProfileEmbeddingMissingError as e:
        print(f"Profile has no embedding — run save_profile first.\n{e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error while matching missions:\n{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
