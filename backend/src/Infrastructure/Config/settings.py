from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "mission-radar-ai"
    APP_ENV: str = "development"
    APP_DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://mission_radar:mission_radar@postgres:5432/mission_radar"

    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    GROQ_API_KEY: str = ""
    LLM_PROVIDER: str = "groq"  # groq | claude
    APIFY_API_TOKEN: str = ""
    APIFY_PROVIDER: str = "mock"  # mock | real

    RESEND_API_KEY: str = ""
    MAIL_FROM: str = "onboarding@resend.dev"
    MAIL_FROM_NAME: str = "Mission Radar AI"
    DIGEST_ENABLED: bool = False

    LANGFUSE_ENABLED: bool = False
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # MCP (Phase 10.0) — identity resolution for the local stdio MCP server
    MISSION_RADAR_PROFILE_ID: str = ""

    # Auth0 (Phase 10.4) — see README "Phase 10.4.1 — Configuration Auth0"
    AUTH0_DOMAIN: str = ""
    AUTH0_API_AUDIENCE: str = ""       # audience of the REST API
    AUTH0_MCP_AUDIENCE: str = ""       # audience of the MCP server resource — kept separate (RFC 8707)

    # MCP (Phase 10.4.5) — Protected Resource Metadata URL advertised in the
    # WWW-Authenticate challenge and served at this same path (see main.py)
    MCP_PROTECTED_RESOURCE_METADATA_URL: str = "http://localhost:8000/.well-known/oauth-protected-resource"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @computed_field
    @property
    def CELERY_BROKER_URL(self) -> str:
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}/"

    @computed_field
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"


settings = Settings()
