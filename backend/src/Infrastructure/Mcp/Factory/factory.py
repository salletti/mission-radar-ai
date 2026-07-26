from typing import Callable, Optional
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError, ToolError

from src.Application.Exception.application_error import PipelineAlreadyRunningError, UserProfileNotFoundError
from src.Application.UseCase.digest_assembler import DigestAssembler
from src.Application.UseCase.get_activity_history import GetActivityHistory
from src.Application.UseCase.get_dashboard_summary import GetDashboardSummary
from src.Application.UseCase.get_mission_details import GetMissionDetails
from src.Application.UseCase.get_pipeline_status import GetPipelineStatus
from src.Application.UseCase.get_today_missions import GetTodayMissions
from src.Application.UseCase.get_user_profile import GetUserProfile
from src.Application.UseCase.search_mission_history import SearchMissionHistory
from src.Application.UseCase.send_digest_now import SendDigestNow
from src.Application.UseCase.start_mission_refresh import StartMissionRefresh
from src.Application.UseCase.update_search_queries import UpdateSearchQueries
from src.Domain.Exception.domain_exceptions import MissionMatchNotFoundError
from src.Domain.Service.digest_generator import DigestGenerator
from src.Domain.Service.digest_mission_selector import DigestMissionSelector
from src.Infrastructure.Config.database import AsyncSessionLocal
from src.Infrastructure.Config.settings import settings
from src.Infrastructure.External.Mailer.jinja_email_template_renderer import JinjaEmailTemplateRenderer
from src.Infrastructure.External.Mailer.resend_mailer_gateway import ResendMailerGateway
from src.Infrastructure.Mcp.Identity.environment_identity_resolver import EnvironmentIdentityResolver
from src.Infrastructure.Mcp.Identity.exceptions import IdentityResolutionError
from src.Infrastructure.Mcp.Identity.identity_resolver import IdentityResolver
from src.Infrastructure.Mcp.Prompt.analyze_profile_prompt import analyze_profile_prompt
from src.Infrastructure.Mcp.Prompt.explain_mission_fit_prompt import explain_mission_fit_prompt
from src.Infrastructure.Mcp.Prompt.prepare_mission_search_prompt import prepare_mission_search_prompt
from src.Infrastructure.Mcp.Prompt.prioritize_today_missions_prompt import prioritize_today_missions_prompt
from src.Infrastructure.Mcp.Prompt.refresh_and_prioritize_missions_prompt import (
    refresh_and_prioritize_missions_prompt,
)
from src.Infrastructure.Mcp.Resource.activity_resource import ActivityResource
from src.Infrastructure.Mcp.Resource.dashboard_resource import DashboardResource
from src.Infrastructure.Mcp.Resource.missions_resource import MissionsResource
from src.Infrastructure.Mcp.Resource.pipeline_resource import PipelineResource
from src.Infrastructure.Mcp.Resource.profile_resource import ProfileResource
from src.Infrastructure.Mcp.Tool.explain_mission_match_tool import ExplainMissionMatchTool
from src.Infrastructure.Mcp.Tool.search_mission_history_tool import SearchMissionHistoryTool
from src.Infrastructure.Mcp.Tool.send_digest_now_tool import SendDigestNowTool
from src.Infrastructure.Mcp.Tool.start_mission_refresh_tool import StartMissionRefreshTool
from src.Infrastructure.Mcp.Tool.update_search_queries_tool import UpdateSearchQueriesTool
from src.Infrastructure.Mcp.Tool.who_am_i_tool import WhoAmITool
from src.Infrastructure.Persistence.Repository.analyzed_post_repository import SqlAlchemyAnalyzedPostRepository
from src.Infrastructure.Persistence.Repository.digest_history_repository import SqlAlchemyDigestHistoryRepository
from src.Infrastructure.Persistence.Repository.mission_match_repository import SqlAlchemyMissionMatchRepository
from src.Infrastructure.Persistence.Repository.pipeline_run_repository import SqlAlchemyPipelineRunRepository
from src.Infrastructure.Persistence.Repository.raw_post_repository import SqlAlchemyRawPostRepository
from src.Infrastructure.Persistence.Repository.search_query_repository import SqlAlchemySearchQueryRepository
from src.Infrastructure.Persistence.Repository.user_profile_repository import SqlAlchemyUserProfileRepository
from src.Infrastructure.Worker.dispatchers.celery_pipeline_dispatcher import CeleryPipelineDispatcher

IdentityResolverFactory = Callable[[], IdentityResolver]


def _default_identity_resolver() -> EnvironmentIdentityResolver:
    return EnvironmentIdentityResolver(profile_id=settings.MISSION_RADAR_PROFILE_ID)


def build_mcp_server(identity_resolver_factory: Optional[IdentityResolverFactory] = None) -> FastMCP:
    """Builds the FastMCP server and registers its tools and resources.

    Process long-lived comme le pilote API : chaque appel de tool/resource ouvre sa propre
    AsyncSession depuis le pool `AsyncSessionLocal` (jamais `CeleryAsyncSessionLocal`,
    dont le NullPool contourne un problème propre à Celery qui ne s'applique pas ici).
    Composition manuelle façon Celery/Commands — FastMCP n'a pas d'équivalent de
    Depends() par appel, donc pas de dossier Dependency/ séparé pour ce périmètre.
    Tools et Resources sont enregistrés par deux fonctions dédiées (Phase 10.2) : au-delà
    d'une poignée d'enregistrements, une seule fonction plate devient difficile à scanner.

    identity_resolver_factory (Phase 10.4.5) : par défaut, EnvironmentIdentityResolver —
    correct pour le pilote stdio local (server.py), où le simple fait de pouvoir spawn le
    process implique déjà la confiance. build_mcp_http_app() passe explicitement un
    JwtIdentityResolver à la place, seul le transport HTTP distant a besoin d'une vraie
    vérification.
    """
    mcp = FastMCP(settings.APP_NAME)

    _identity_resolver = identity_resolver_factory or _default_identity_resolver

    _register_tools(mcp, _identity_resolver)
    _register_resources(mcp, _identity_resolver)
    _register_prompts(mcp)

    return mcp


def _register_tools(mcp: FastMCP, identity_resolver: IdentityResolverFactory) -> None:
    @mcp.tool
    async def whoami() -> dict:
        """Return the identity resolved for this MCP session and whether it matches a UserProfile."""
        async with AsyncSessionLocal() as session:
            get_user_profile = GetUserProfile(user_profile_repository=SqlAlchemyUserProfileRepository(session))
            tool = WhoAmITool(identity_resolver=identity_resolver(), get_user_profile=get_user_profile)
            try:
                return await tool.execute()
            except IdentityResolutionError as exc:
                raise ToolError(str(exc)) from exc

    @mcp.tool
    async def explain_mission_match(mission_match_id: UUID) -> dict:
        """Explain why a specific mission match scored the way it did for the current user.

        Use this when the user asks why a particular mission was suggested, wants a
        breakdown of the match score (semantic/contract/remote/TJM), or wants to know
        which of their skills matched or are missing for that mission. Takes the
        `mission_match_id` of a mission already surfaced by another Resource or Tool
        (e.g. `mission-radar://missions`, `search_mission_history`) — it does not list
        or search missions itself, and it does not return the original LinkedIn post
        content (only the computed explanation).
        """
        async with AsyncSessionLocal() as session:
            get_mission_details = GetMissionDetails(
                mission_match_repository=SqlAlchemyMissionMatchRepository(session),
                analyzed_post_repository=SqlAlchemyAnalyzedPostRepository(session),
                raw_post_repository=SqlAlchemyRawPostRepository(session),
                user_profile_repository=SqlAlchemyUserProfileRepository(session),
            )
            tool = ExplainMissionMatchTool(
                identity_resolver=identity_resolver(), get_mission_details=get_mission_details
            )
            try:
                return await tool.execute(mission_match_id)
            except IdentityResolutionError as exc:
                raise ToolError(str(exc)) from exc
            except (MissionMatchNotFoundError, UserProfileNotFoundError) as exc:
                raise ToolError(str(exc)) from exc

    @mcp.tool
    async def search_mission_history(
        keyword: str | None = None,
        min_score: float = 0.0,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Search the current user's full mission match history by keyword.

        Use this when the user wants to find a specific past mission by title, company
        name, or detected technology stack (e.g. "find the Kubernetes mission from last
        week"), rather than just browsing the most recent ones. Unlike
        `mission-radar://missions` (a fixed top-20 view), this searches across the
        user's entire match history and supports pagination via `limit`/`offset`. Pass
        `keyword=None` to browse the full history without filtering.
        """
        async with AsyncSessionLocal() as session:
            search_mission_history_uc = SearchMissionHistory(
                mission_match_repository=SqlAlchemyMissionMatchRepository(session),
                analyzed_post_repository=SqlAlchemyAnalyzedPostRepository(session),
                raw_post_repository=SqlAlchemyRawPostRepository(session),
            )
            tool = SearchMissionHistoryTool(
                identity_resolver=identity_resolver(), search_mission_history=search_mission_history_uc
            )
            try:
                return await tool.execute(keyword=keyword, min_score=min_score, limit=limit, offset=offset)
            except IdentityResolutionError as exc:
                raise ToolError(str(exc)) from exc

    @mcp.tool
    async def start_mission_refresh() -> dict:
        """Trigger a new mission refresh for the current user right now.

        Use this when the user asks to refresh, re-scan, or check for new missions
        immediately, rather than waiting for the next scheduled run — it's the
        conversational equivalent of the "Refresh" button in the Dashboard. Runs
        collect → analyze → match asynchronously and, if eligible, sends a digest
        email. Returns the created PipelineRun (status `pending`); use
        `mission-radar://pipeline` afterwards to poll its progress. Raises an error
        if a pipeline is already running for this user — only one refresh can run
        at a time.
        """
        async with AsyncSessionLocal() as session:
            start_mission_refresh_uc = StartMissionRefresh(
                pipeline_run_repo=SqlAlchemyPipelineRunRepository(session),
                user_profile_repo=SqlAlchemyUserProfileRepository(session),
                dispatcher=CeleryPipelineDispatcher(),
            )
            tool = StartMissionRefreshTool(
                identity_resolver=identity_resolver(), start_mission_refresh=start_mission_refresh_uc
            )
            try:
                result = await tool.execute()
            except IdentityResolutionError as exc:
                raise ToolError(str(exc)) from exc
            except (PipelineAlreadyRunningError, UserProfileNotFoundError) as exc:
                raise ToolError(str(exc)) from exc
            await session.commit()
            return result

    @mcp.tool
    async def update_search_queries(queries: list[str]) -> dict:
        """Replace the current user's LinkedIn search queries with a new full list.

        Use this when the user wants to change what Mission Radar AI searches for
        (e.g. "search for Kubernetes and Terraform missions instead of Python",
        "add 'lead dev python freelance' to my searches"). This REPLACES the
        entire list of queries — it is not additive. If the user wants to keep
        their existing queries and only add one, ask them to restate the full
        list first. Empty or invalid entries are silently dropped. Returns the
        number of queries actually saved.
        """
        async with AsyncSessionLocal() as session:
            update_search_queries_uc = UpdateSearchQueries(search_query_repo=SqlAlchemySearchQueryRepository(session))
            tool = UpdateSearchQueriesTool(
                identity_resolver=identity_resolver(), update_search_queries=update_search_queries_uc
            )
            try:
                result = await tool.execute(queries)
            except IdentityResolutionError as exc:
                raise ToolError(str(exc)) from exc
            await session.commit()
            return result

    @mcp.tool
    async def send_digest_now() -> dict:
        """Send the current user's daily digest email right now, on demand.

        Use this when the user explicitly asks to receive their mission digest by
        email immediately (e.g. "email me my top missions now"), independent of
        the automatic daily schedule. Builds the digest from the user's current
        top-scored missions and sends it via the configured mailer. Returns
        `status` ("sent" or "failed") and `missions_count` — a `missions_count`
        of 0 with `status: "sent"` means the email was sent but there were no
        qualifying missions to include, not an error.
        """
        if not settings.DIGEST_ENABLED:
            raise ToolError("Digest sending is disabled in this environment (DIGEST_ENABLED=false)")

        async with AsyncSessionLocal() as session:
            digest_assembler = DigestAssembler(
                user_profile_repository=SqlAlchemyUserProfileRepository(session),
                mission_match_repository=SqlAlchemyMissionMatchRepository(session),
                analyzed_post_repository=SqlAlchemyAnalyzedPostRepository(session),
                raw_post_repository=SqlAlchemyRawPostRepository(session),
                selector=DigestMissionSelector(),
                generator=DigestGenerator(),
            )
            send_digest_now_uc = SendDigestNow(
                digest_assembler=digest_assembler,
                renderer=JinjaEmailTemplateRenderer(),
                mailer=ResendMailerGateway(
                    api_key=settings.RESEND_API_KEY,
                    from_email=settings.MAIL_FROM,
                    from_name=settings.MAIL_FROM_NAME,
                ),
                digest_history_repository=SqlAlchemyDigestHistoryRepository(session),
            )
            tool = SendDigestNowTool(identity_resolver=identity_resolver(), send_digest_now=send_digest_now_uc)
            try:
                result = await tool.execute()
            except IdentityResolutionError as exc:
                raise ToolError(str(exc)) from exc
            except UserProfileNotFoundError as exc:
                raise ToolError(str(exc)) from exc
            await session.commit()
            return result


def _register_resources(mcp: FastMCP, identity_resolver: IdentityResolverFactory) -> None:
    @mcp.resource("mission-radar://profile")
    async def profile() -> dict:
        """Return the current user's profile."""
        async with AsyncSessionLocal() as session:
            get_user_profile = GetUserProfile(user_profile_repository=SqlAlchemyUserProfileRepository(session))
            resource = ProfileResource(identity_resolver=identity_resolver(), get_user_profile=get_user_profile)
            try:
                return await resource.execute()
            except IdentityResolutionError as exc:
                raise ResourceError(str(exc)) from exc

    @mcp.resource("mission-radar://dashboard")
    async def dashboard() -> dict:
        """Return the current user's dashboard summary (KPIs + pipeline health)."""
        async with AsyncSessionLocal() as session:
            get_dashboard_summary = GetDashboardSummary(
                mission_match_repository=SqlAlchemyMissionMatchRepository(session),
                pipeline_run_repository=SqlAlchemyPipelineRunRepository(session),
            )
            resource = DashboardResource(
                identity_resolver=identity_resolver(), get_dashboard_summary=get_dashboard_summary
            )
            try:
                return await resource.execute()
            except IdentityResolutionError as exc:
                raise ResourceError(str(exc)) from exc

    @mcp.resource("mission-radar://missions")
    async def missions() -> dict:
        """Return the current user's top-scored missions for today."""
        async with AsyncSessionLocal() as session:
            get_today_missions = GetTodayMissions(
                mission_match_repository=SqlAlchemyMissionMatchRepository(session),
                analyzed_post_repository=SqlAlchemyAnalyzedPostRepository(session),
                raw_post_repository=SqlAlchemyRawPostRepository(session),
            )
            resource = MissionsResource(identity_resolver=identity_resolver(), get_today_missions=get_today_missions)
            try:
                return await resource.execute()
            except IdentityResolutionError as exc:
                raise ResourceError(str(exc)) from exc

    @mcp.resource("mission-radar://activity")
    async def activity() -> dict:
        """Return the current user's recent activity timeline (mission matches + digests sent)."""
        async with AsyncSessionLocal() as session:
            get_activity_history = GetActivityHistory(
                mission_match_repository=SqlAlchemyMissionMatchRepository(session),
                analyzed_post_repository=SqlAlchemyAnalyzedPostRepository(session),
                raw_post_repository=SqlAlchemyRawPostRepository(session),
                digest_history_repository=SqlAlchemyDigestHistoryRepository(session),
            )
            resource = ActivityResource(identity_resolver=identity_resolver(), get_activity_history=get_activity_history)
            try:
                return await resource.execute()
            except IdentityResolutionError as exc:
                raise ResourceError(str(exc)) from exc

    @mcp.resource("mission-radar://pipeline")
    async def pipeline() -> dict:
        """Return the current user's latest pipeline run, if any."""
        async with AsyncSessionLocal() as session:
            get_pipeline_status = GetPipelineStatus(pipeline_run_repository=SqlAlchemyPipelineRunRepository(session))
            resource = PipelineResource(
                identity_resolver=identity_resolver(), get_pipeline_status=get_pipeline_status
            )
            try:
                return await resource.execute()
            except IdentityResolutionError as exc:
                raise ResourceError(str(exc)) from exc


def _register_prompts(mcp: FastMCP) -> None:
    @mcp.prompt
    def analyze_profile() -> str:
        """Guide a structured analysis of the current user's profile: stack coverage,
        TJM positioning, contract/remote fit, and completeness."""
        return analyze_profile_prompt()

    @mcp.prompt
    def prepare_mission_search(keyword: str | None = None) -> str:
        """Guide preparing a mission search: check pipeline freshness first, then
        search the user's mission history by keyword."""
        return prepare_mission_search_prompt(keyword)

    @mcp.prompt
    def explain_mission_fit(mission_match_id: UUID) -> str:
        """Guide turning a mission match's score breakdown into a plain-language,
        decision-oriented explanation for the user."""
        return explain_mission_fit_prompt(mission_match_id)

    @mcp.prompt
    def prioritize_today_missions() -> str:
        """Guide ranking today's missions using profile context and per-mission
        match explanations, to help the user decide what to look at first."""
        return prioritize_today_missions_prompt()

    @mcp.prompt
    def refresh_and_prioritize_missions() -> str:
        """Guide triggering a fresh mission refresh, checking the pipeline until it
        completes, then prioritizing today's missions using profile context and
        per-mission match explanations."""
        return refresh_and_prioritize_missions_prompt()
