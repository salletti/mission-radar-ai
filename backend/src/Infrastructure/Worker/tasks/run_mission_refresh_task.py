import asyncio
import logging
from datetime import datetime, timezone
from functools import lru_cache
from uuid import UUID

from src.Application.DTO.collect_posts_command import CollectPostsCommand
from src.Application.UseCase.analyze_raw_post import AnalyzeRawPost
from src.Application.UseCase.collect_raw_posts import CollectRawPosts
from src.Application.UseCase.generate_digest import GenerateDigest
from src.Application.UseCase.match_missions import MatchMissions
from src.Application.UseCase.save_raw_posts import SaveRawPosts
from src.Application.UseCase.send_digest import SendDigest
from src.Domain.Service.digest_generator import DigestGenerator
from src.Domain.Service.digest_mission_selector import DigestMissionSelector
from src.Domain.Service.digest_policy import DigestPolicy
from src.Domain.Service.mission_embedding_builder import MissionEmbeddingBuilder
from src.Domain.Service.mission_match_scorer import MissionMatchScorer
from src.Domain.Service.mission_normalizer import MissionNormalizer
from src.Domain.ValueObject.pipeline_enums import PipelineStatus, PipelineStep, StepOutcome
from src.Infrastructure.Config.database import CeleryAsyncSessionLocal as AsyncSessionLocal
from src.Infrastructure.Config.settings import settings
from src.Infrastructure.External.Apify.apify_scraper_gateway import ApifyScraperGateway
from src.Infrastructure.External.Apify.mock_apify_provider import MockApifyProvider
from src.Infrastructure.External.Apify.real_apify_provider import RealApifyProvider
from src.Infrastructure.External.Embedding.sentence_transformer_embedding_gateway import SentenceTransformerEmbeddingGateway
from src.Infrastructure.External.LLM.groq_llm_gateway import GroqLLMGateway
from src.Infrastructure.External.Mailer.jinja_email_template_renderer import JinjaEmailTemplateRenderer
from src.Infrastructure.External.Observability.langfuse.factory import get_langfuse_tracer
from src.Infrastructure.External.Mailer.resend_mailer_gateway import ResendMailerGateway
from src.Infrastructure.Persistence.Repository.analyzed_post_repository import SqlAlchemyAnalyzedPostRepository
from src.Infrastructure.Persistence.Repository.mission_match_repository import SqlAlchemyMissionMatchRepository
from src.Infrastructure.Persistence.Repository.pipeline_run_repository import SqlAlchemyPipelineRunRepository
from src.Infrastructure.Persistence.Repository.raw_post_repository import SqlAlchemyRawPostRepository
from src.Infrastructure.Persistence.Repository.search_query_raw_post_repository import SqlAlchemySearchQueryRawPostRepository
from src.Infrastructure.Persistence.Repository.search_query_repository import SqlAlchemySearchQueryRepository
from src.Infrastructure.Persistence.Repository.user_profile_repository import SqlAlchemyUserProfileRepository
from src.Infrastructure.Worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_embedding_gateway() -> SentenceTransformerEmbeddingGateway:
    """Singleton — loads all-MiniLM-L6-v2 once per worker process."""
    return SentenceTransformerEmbeddingGateway()


@celery_app.task(name="tasks.run_mission_refresh", ignore_result=True, bind=True, max_retries=5)
def run_mission_refresh(self, pipeline_run_id: str, user_id: str) -> None:
    """Celery task: orchestrates collect → analyze → match for a single user pipeline run."""
    asyncio.run(_run_refresh(self, pipeline_run_id, user_id))


async def _run_refresh(task, pipeline_run_id_str: str, user_id_str: str) -> None:
    pipeline_run_id = UUID(pipeline_run_id_str)
    user_id = UUID(user_id_str)

    async with AsyncSessionLocal() as session:
        repo = SqlAlchemyPipelineRunRepository(session)
        run = await repo.get_by_id(pipeline_run_id)

        if run is None:
            # PipelineRun not yet committed by the API — retry after 1s (race condition guard)
            raise task.retry(countdown=1)

        if run.status == PipelineStatus.RUNNING and task.request.retries > 0:
            # Worker crashed mid-run — reset to PENDING+COLLECT so this retry restarts cleanly
            logger.warning(
                "run_mission_refresh: PipelineRun %s found RUNNING on retry %d — resetting to PENDING",
                pipeline_run_id,
                task.request.retries,
            )
            run.status = PipelineStatus.PENDING
            run.current_step = PipelineStep.COLLECT
            run.progress = 0.0
            await repo.update(run)
            await session.commit()

        if run.status != PipelineStatus.PENDING:
            logger.warning(
                "run_mission_refresh: PipelineRun %s already in status %s — skipping duplicate execution",
                pipeline_run_id,
                run.status,
            )
            return

        run.start()  # PENDING → RUNNING, progress auto-set to COLLECT value (0.33)
        await repo.update(run)
        await session.commit()

    logger.info("run_mission_refresh: started pipeline_run=%s user=%s", pipeline_run_id, user_id)

    try:
        new_post_ids = await _collect_step(pipeline_run_id, user_id)
        await _analyze_step(pipeline_run_id, new_post_ids)
        await _match_step(pipeline_run_id, user_id)

        # Advance to DIGEST step and capture trigger_type for DigestPolicy
        async with AsyncSessionLocal() as session:
            repo = SqlAlchemyPipelineRunRepository(session)
            run = await repo.get_by_id(pipeline_run_id)
            run.advance_to_step(PipelineStep.DIGEST)
            trigger_type = run.trigger_type
            await repo.update(run)
            await session.commit()

        # DigestPolicy gates whether an email is actually sent; DIGEST_ENABLED allows disabling via env
        should_send = settings.DIGEST_ENABLED and DigestPolicy().should_send(trigger_type)
        digest_sent = False
        if should_send:
            digest_sent = await _digest_step(pipeline_run_id, user_id)

        # Record outcome, advance to DONE, complete
        async with AsyncSessionLocal() as session:
            repo = SqlAlchemyPipelineRunRepository(session)
            run = await repo.get_by_id(pipeline_run_id)
            run.record_step_outcome(
                PipelineStep.DIGEST,
                StepOutcome.EXECUTED if (should_send and digest_sent) else
                StepOutcome.FAILED   if (should_send and not digest_sent) else
                StepOutcome.SKIPPED,
            )
            run.advance_to_step(PipelineStep.DONE)
            run.complete()  # RUNNING → COMPLETED
            await repo.update(run)
            await session.commit()

        logger.info(
            "run_mission_refresh: completed pipeline_run=%s new_posts=%d digest=%s",
            pipeline_run_id,
            len(new_post_ids),
            StepOutcome.EXECUTED.value if (should_send and digest_sent) else
            StepOutcome.FAILED.value   if (should_send and not digest_sent) else
            StepOutcome.SKIPPED.value,
        )
    except Exception as exc:
        logger.exception("run_mission_refresh: failed pipeline_run=%s error=%s", pipeline_run_id, exc)
        async with AsyncSessionLocal() as session:
            repo = SqlAlchemyPipelineRunRepository(session)
            run = await repo.get_by_id(pipeline_run_id)
            if run is not None and run.status == PipelineStatus.RUNNING:
                run.fail(str(exc))
                await repo.update(run)
                await session.commit()
        raise


async def _collect_step(pipeline_run_id: UUID, user_id: UUID) -> list[UUID]:
    if settings.APIFY_PROVIDER == "real":
        provider = RealApifyProvider(settings.APIFY_API_TOKEN)
    else:
        provider = MockApifyProvider()
    gateway = ApifyScraperGateway(provider)

    async with AsyncSessionLocal() as session:
        sq_repo = SqlAlchemySearchQueryRepository(session)
        queries = await sq_repo.get_by_profile(user_id)

        raw_repo = SqlAlchemyRawPostRepository(session)
        link_repo = SqlAlchemySearchQueryRawPostRepository(session)

        new_post_ids: list[UUID] = []

        for query in queries:
            posts = await CollectRawPosts(gateway).execute(
                CollectPostsCommand(query=query.query, limit=query.limit)
            )
            result = await SaveRawPosts(raw_repo, link_repo).execute(posts, query.id)
            new_post_ids.extend(result.new_post_ids)
            logger.info(
                "run_mission_refresh: collect query=%r saved=%d skipped=%d",
                query.query,
                result.saved,
                result.skipped,
            )

        run_repo = SqlAlchemyPipelineRunRepository(session)
        run = await run_repo.get_by_id(pipeline_run_id)
        run.advance_to_step(PipelineStep.ANALYZE)  # progress auto-set to 0.66
        await run_repo.update(run)
        await session.commit()

    return new_post_ids


async def _analyze_step(pipeline_run_id: UUID, new_post_ids: list[UUID]) -> None:
    for post_id in new_post_ids:
        async with AsyncSessionLocal() as session:
            try:
                raw_repo = SqlAlchemyRawPostRepository(session)
                raw_post = await raw_repo.get_by_id(post_id)
                if raw_post is None:
                    logger.warning("run_mission_refresh: RawPost %s not found — skipping", post_id)
                    continue

                llm = GroqLLMGateway(settings.GROQ_API_KEY, tracer=get_langfuse_tracer())
                analyzed_repo = SqlAlchemyAnalyzedPostRepository(session)
                use_case = AnalyzeRawPost(
                    llm=llm,
                    mission_normalizer=MissionNormalizer(),
                    mission_embedding_builder=MissionEmbeddingBuilder(),
                    embedding_gateway=_get_embedding_gateway(),
                    analyzed_post_repository=analyzed_repo,
                )
                result = await use_case.execute(raw_post)
                await session.commit()

                logger.info(
                    "run_mission_refresh: analyzed raw_post=%s status=%s",
                    post_id,
                    result.status,
                )
            except Exception as e:
                logger.warning("run_mission_refresh: analyze skipped raw_post=%s error=%s", post_id, e)

    async with AsyncSessionLocal() as session:
        run_repo = SqlAlchemyPipelineRunRepository(session)
        run = await run_repo.get_by_id(pipeline_run_id)
        run.advance_to_step(PipelineStep.MATCH)  # progress auto-set to 0.75
        await run_repo.update(run)
        await session.commit()


async def _match_step(pipeline_run_id: UUID, user_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        user_repo = SqlAlchemyUserProfileRepository(session)
        profile = await user_repo.get_by_id(user_id)
        if profile is None:
            raise ValueError(f"UserProfile {user_id} not found during match step")

        scorer = MissionMatchScorer(_get_embedding_gateway())
        use_case = MatchMissions(
            scorer=scorer,
            search_query_repository=SqlAlchemySearchQueryRepository(session),
            search_query_raw_post_repository=SqlAlchemySearchQueryRawPostRepository(session),
            analyzed_post_repository=SqlAlchemyAnalyzedPostRepository(session),
            mission_match_repository=SqlAlchemyMissionMatchRepository(session),
        )
        await use_case.execute(profile)
        await session.commit()


async def _digest_step(pipeline_run_id: UUID, user_id: UUID) -> bool:
    from src.Domain.Entity.digest_history import DigestHistory, DigestStatus
    from src.Infrastructure.Persistence.Repository.digest_history_repository import SqlAlchemyDigestHistoryRepository
    from src.Infrastructure.Persistence.Repository.sent_mission_repository import SqlAlchemySentMissionRepository

    async with AsyncSessionLocal() as session:
        digest = await GenerateDigest(
            user_profile_repository=SqlAlchemyUserProfileRepository(session),
            mission_match_repository=SqlAlchemyMissionMatchRepository(session),
            analyzed_post_repository=SqlAlchemyAnalyzedPostRepository(session),
            raw_post_repository=SqlAlchemyRawPostRepository(session),
            selector=DigestMissionSelector(),
            generator=DigestGenerator(),
            sent_mission_repository=SqlAlchemySentMissionRepository(session),
        ).execute(user_id)

    missions_count = digest.mission_count
    provider_message_id: str | None = None
    error_message: str | None = None
    status = DigestStatus.SENT

    try:
        provider_message_id = await SendDigest(
            renderer=JinjaEmailTemplateRenderer(),
            mailer=ResendMailerGateway(
                api_key=settings.RESEND_API_KEY,
                from_email=settings.MAIL_FROM,
                from_name=settings.MAIL_FROM_NAME,
            ),
        ).execute(digest)
    except Exception as exc:
        status = DigestStatus.FAILED
        error_message = str(exc)
        logger.warning("_digest_step: send failed pipeline_run=%s error=%s", pipeline_run_id, exc)

    history = DigestHistory(
        user_id=user_id,
        pipeline_run_id=pipeline_run_id,
        sent_at=datetime.now(timezone.utc),
        status=status,
        missions_count=missions_count if status == DigestStatus.SENT else 0,
        provider_message_id=provider_message_id,
        error_message=error_message,
    )

    async with AsyncSessionLocal() as session:
        if status == DigestStatus.SENT and digest.missions:
            await SqlAlchemySentMissionRepository(session).save_many(
                user_id,
                [m.analyzed_post_id for m in digest.missions],
                history.sent_at,
            )
        await SqlAlchemyDigestHistoryRepository(session).save(history)
        await session.commit()

    return status == DigestStatus.SENT
