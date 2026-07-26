from __future__ import annotations

import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from groq import AsyncGroq
from pydantic import BaseModel, Field, ValidationError

from src.Application.DTO.cv_profile import CVProfile
from src.Application.Gateway.llm_gateway import LLMGateway
from src.Domain.ValueObject.post_analysis import PostAnalysis
from src.Infrastructure.External.LLM.analyze_post_prompt_builder import build_analyze_post_prompt
from src.Infrastructure.External.LLM.analyze_post_response_schema import ANALYZE_POST_JSON_SCHEMA
from src.Infrastructure.External.LLM.exceptions import (
    AnalyzePostParsingError,
    LLMExtractionError,
    LLMResponseFormatError,
)
from src.Infrastructure.External.Observability.langfuse.llm_tracer import LLMTracer
from src.Infrastructure.External.Observability.langfuse.null_tracer import NullTracer

_PROMPTS_DIR = Path(__file__).parent / "prompts"

# Groq's strict structured-outputs mode (constrained decoding) is only
# supported by these models as of console.groq.com/docs/structured-outputs.
_STRICT_JSON_SCHEMA_CAPABLE_MODELS = frozenset({"openai/gpt-oss-20b", "openai/gpt-oss-120b"})


@lru_cache(maxsize=None)
def _load_prompt(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text(encoding="utf-8")


class _CVProfileRaw(BaseModel):
    """Pydantic validation model for the raw LLM JSON response."""

    email: str
    full_name: str
    title: str
    years_experience: Optional[int] = None
    preferred_contract_type: Optional[str] = None
    target_tjm: Optional[float] = None
    preferred_remote_mode: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    availability: str = "immediate"
    location: Optional[str] = None


class _SearchQueryItem(BaseModel):
    query: str
    source: str = "linkedin"
    limit: int = 50


class _SearchQueriesResponse(BaseModel):
    queries: list[_SearchQueryItem]


def _parse_availability(value: str) -> datetime:
    if value.lower() == "immediate":
        return datetime.now(UTC)
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


class GroqLLMGateway(LLMGateway):
    """LLM gateway backed by Groq API (llama-3.3-70b-versatile by default).

    The _client parameter accepts an injected fake for unit tests, avoiding
    any real network calls — same injection pattern as Python's stdlib adapters.
    """

    _PROMPT_VERSION = "v1"

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        _client: Any = None,
        tracer: LLMTracer | None = None,
        strict_json_schema: bool = False,
    ) -> None:
        if strict_json_schema and model not in _STRICT_JSON_SCHEMA_CAPABLE_MODELS:
            raise ValueError(
                f"strict_json_schema=True requires a model in "
                f"{sorted(_STRICT_JSON_SCHEMA_CAPABLE_MODELS)}, got {model!r}"
            )
        self._client = _client or AsyncGroq(api_key=api_key, timeout=30.0)
        self._model = model
        self._tracer = tracer or NullTracer()
        self._strict_json_schema = strict_json_schema

    async def _create_completion(
        self,
        *,
        trace_name: str,
        messages: list[dict[str, str]],
        response_format: dict | None = None,
        temperature: float = 0,
    ) -> Any:
        system_prompt = next((m["content"] for m in messages if m["role"] == "system"), None)
        handle = self._tracer.start_completion(
            name=trace_name,
            provider="groq",
            model=self._model,
            prompt_version=self._PROMPT_VERSION,
            system_prompt=system_prompt,
            messages=messages,
        )

        kwargs: dict[str, Any] = {"model": self._model, "messages": messages, "temperature": temperature}
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except Exception as e:
            handle.fail(error=e)
            raise LLMExtractionError(reason=str(e)) from e

        usage = getattr(response, "usage", None)
        handle.succeed(
            output=response.choices[0].message.content,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            total_tokens=getattr(usage, "total_tokens", None),
        )
        return response

    async def extract_profile_from_cv(self, cv_text: str) -> CVProfile:
        prompt = _load_prompt("cv_profile_extraction.txt")
        response = await self._create_completion(
            trace_name="extract_profile_from_cv",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": cv_text},
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMResponseFormatError(reason=f"invalid JSON: {e}") from e

        try:
            raw = _CVProfileRaw.model_validate(data)
        except ValidationError as e:
            raise LLMResponseFormatError(reason=str(e)) from e

        try:
            availability = _parse_availability(raw.availability)
        except (ValueError, AttributeError) as e:
            raise LLMResponseFormatError(reason=f"invalid availability value: {e}") from e

        return CVProfile(
            email=raw.email,
            full_name=raw.full_name,
            title=raw.title,
            years_experience=raw.years_experience or 0,
            preferred_contract_type=raw.preferred_contract_type or "unknown",
            target_tjm=raw.target_tjm or 0.0,
            preferred_remote_mode=raw.preferred_remote_mode or "unknown",
            skills=tuple(s.lower() for s in raw.skills),
            availability=availability,
            location=raw.location,
        )

    async def summarize_mission(self, content: str) -> str:
        response = await self._create_completion(
            trace_name="summarize_mission",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Summarize this LinkedIn job post in 2-3 sentences, "
                        "focusing on the role, required skills, and contract type:\n\n"
                        f"{content}"
                    ),
                }
            ],
        )

        return response.choices[0].message.content

    async def generate_search_queries(self, profile: "UserProfile") -> list[dict]:
        from src.Domain.Entity.user_profile import UserProfile  # noqa: F401

        system_prompt = _load_prompt("search_query_generation.txt")
        skills_str = ", ".join(profile.skills.technologies) or "none"
        user_message = (
            f"Candidate profile:\n"
            f"- Title: {profile.title}\n"
            f"- Declared skills: {skills_str}\n"
            f"- Location: {profile.location or 'not specified'}\n"
            f"- Contract type: {profile.preferred_contract_type.value}\n"
            f"- Remote preference: {profile.preferred_remote_mode.value}\n\n"
            f"Full CV text (analyze carefully for technology frequency and depth):\n"
            f"{profile.cv_raw_text or ''}"
        )

        response = await self._create_completion(
            trace_name="generate_search_queries",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content

        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise LLMResponseFormatError(reason=f"invalid JSON: {e}") from e

        try:
            validated = _SearchQueriesResponse.model_validate(data)
        except ValidationError as e:
            raise LLMResponseFormatError(reason=str(e)) from e

        return [q.model_dump() for q in validated.queries]

    async def analyze_post(self, raw_post: "RawPost") -> PostAnalysis:
        prompt = build_analyze_post_prompt(raw_post)
        response_format = ANALYZE_POST_JSON_SCHEMA if self._strict_json_schema else {"type": "json_object"}
        response = await self._create_completion(
            trace_name="analyze_post",
            messages=[{"role": "user", "content": prompt}],
            response_format=response_format,
        )

        content = response.choices[0].message.content
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise AnalyzePostParsingError(reason=f"invalid JSON: {e}") from e

        return PostAnalysis.from_llm_payload(data)
