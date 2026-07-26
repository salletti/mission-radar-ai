from __future__ import annotations

import logging
from functools import lru_cache

from langfuse import Langfuse

from src.Infrastructure.Config.settings import settings
from src.Infrastructure.External.Observability.langfuse.langfuse_tracer import LangfuseTracer
from src.Infrastructure.External.Observability.langfuse.llm_tracer import LLMTracer
from src.Infrastructure.External.Observability.langfuse.null_tracer import NullTracer

logger = logging.getLogger(__name__)


# Lazy singleton — evaluated on first real use, not at import time, so a missing
# or misconfigured Langfuse setup can never crash app startup. Same pattern as
# _get_llm_gateway() in Infrastructure/Api/Dependency/dependencies.py.
@lru_cache(maxsize=1)
def get_langfuse_tracer() -> LLMTracer:
    if not settings.LANGFUSE_ENABLED:
        return NullTracer()
    try:
        client = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
        )
        return LangfuseTracer(client=client, environment=settings.APP_ENV)
    except Exception:
        logger.warning("Langfuse init failed — falling back to NullTracer", exc_info=True)
        return NullTracer()
