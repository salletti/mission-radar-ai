from fastapi import FastAPI

from src.Infrastructure.Api.Controller.dashboard_controller import router as dashboard_router
from src.Infrastructure.Api.Controller.health import router as health_router
from src.Infrastructure.Api.Controller.onboarding_controller import router as onboarding_router
from src.Infrastructure.Api.Controller.pipeline_controller import router as pipeline_router
from src.Infrastructure.Api.Controller.tasks import router as tasks_router
from src.Infrastructure.Api.Controller.users_controller import router as users_router
from src.Infrastructure.Config.settings import settings
from src.Infrastructure.Mcp.Transport.http_app_factory import build_mcp_http_app

mcp_app = build_mcp_http_app()

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    debug=settings.APP_DEBUG,
    lifespan=mcp_app.lifespan,
)
app.include_router(health_router)
app.include_router(tasks_router)
app.include_router(onboarding_router)
app.include_router(dashboard_router)
app.include_router(users_router)
app.include_router(pipeline_router)
app.mount("/mcp", mcp_app)


@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata() -> dict:
    """RFC 9728 Protected Resource Metadata for the MCP server mount — tells an
    MCP client which Authorization Server (Auth0) to use for the `resource`
    identified by AUTH0_MCP_AUDIENCE (MCP Authorization spec, Phase 10.4.5)."""
    return {
        "resource": settings.AUTH0_MCP_AUDIENCE,
        "authorization_servers": [f"https://{settings.AUTH0_DOMAIN}/"],
        "bearer_methods_supported": ["header"],
    }
