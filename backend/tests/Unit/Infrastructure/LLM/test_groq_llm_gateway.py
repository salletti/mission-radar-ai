"""Unit tests for GroqLLMGateway.

A FakeGroqClient is injected via the _client parameter — no real Groq API calls.
Tests cover the parsing and validation logic of the gateway.
"""
import json
import types
from datetime import UTC, datetime, date
from uuid import uuid4

import pytest

from src.Application.DTO.cv_profile import CVProfile
from src.Domain.Entity.raw_post import RawPost
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Exception.domain_exceptions import EmptyAnalysisSummaryError
from src.Domain.ValueObject.post_analysis import PostAnalysis
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack
from src.Infrastructure.External.LLM.exceptions import (
    AnalyzePostParsingError,
    LLMExtractionError,
    LLMResponseFormatError,
)
from src.Infrastructure.External.LLM.analyze_post_response_schema import ANALYZE_POST_JSON_SCHEMA
from src.Infrastructure.External.LLM.groq_llm_gateway import GroqLLMGateway

# ---------------------------------------------------------------------------
# Fake Groq client
# ---------------------------------------------------------------------------

_VALID_JSON = json.dumps(
    {
        "email": "jean.dupont@example.com",
        "full_name": "Jean Dupont",
        "title": "Senior Python Developer",
        "years_experience": 10,
        "preferred_contract_type": "freelance",
        "target_tjm": 700.0,
        "preferred_remote_mode": "full_remote",
        "skills": ["Python", "FastAPI", "Docker"],
        "availability": "immediate",
        "location": "Paris",
    }
)


class _FakeGroqClient:
    """Mimics groq.AsyncGroq — proxies .chat.completions.create to a configurable coroutine."""

    def __init__(self, response_content: str, usage: object = None) -> None:
        self._content = response_content
        self._usage = usage
        self.create_calls: list[dict] = []

    @property
    def chat(self) -> "_FakeGroqClient":
        return self

    @property
    def completions(self) -> "_FakeGroqClient":
        return self

    async def create(self, **kwargs):
        self.create_calls.append(kwargs)
        msg = types.SimpleNamespace(content=self._content)
        choice = types.SimpleNamespace(message=msg)
        namespace_kwargs = {"choices": [choice]}
        if self._usage is not None:
            namespace_kwargs["usage"] = self._usage
        return types.SimpleNamespace(**namespace_kwargs)


class _SpyTraceHandle:
    def __init__(self, calls: list[dict], name: str) -> None:
        self._calls = calls
        self._name = name

    def succeed(self, **kwargs) -> None:
        self._calls.append({"event": "succeed", "trace_name": self._name, **kwargs})

    def fail(self, **kwargs) -> None:
        self._calls.append({"event": "fail", "trace_name": self._name, **kwargs})


class _SpyTracer:
    """Hand-rolled LLMTracer fake that records every start_completion call."""

    def __init__(self) -> None:
        self.start_completion_calls: list[dict] = []
        self.handle_calls: list[dict] = []

    def start_completion(self, **kwargs) -> _SpyTraceHandle:
        self.start_completion_calls.append(kwargs)
        return _SpyTraceHandle(self.handle_calls, kwargs["name"])


class _ErrorGroqClient:
    """Mimics groq.AsyncGroq — always raises an exception on create."""

    @property
    def chat(self) -> "_ErrorGroqClient":
        return self

    @property
    def completions(self) -> "_ErrorGroqClient":
        return self

    async def create(self, **kwargs):
        raise RuntimeError("Groq API unavailable")


def _make_gateway(response_content: str) -> GroqLLMGateway:
    return GroqLLMGateway(api_key="fake", _client=_FakeGroqClient(response_content))


# ---------------------------------------------------------------------------
# Nominal extraction
# ---------------------------------------------------------------------------


async def test_extract_valid_profile() -> None:
    gateway = _make_gateway(_VALID_JSON)

    result = await gateway.extract_profile_from_cv("some cv text")

    assert isinstance(result, CVProfile)
    assert result.email == "jean.dupont@example.com"
    assert result.full_name == "Jean Dupont"
    assert result.title == "Senior Python Developer"
    assert result.years_experience == 10
    assert result.preferred_contract_type == "freelance"
    assert result.target_tjm == 700.0
    assert result.preferred_remote_mode == "full_remote"
    assert set(result.skills) == {"python", "fastapi", "docker"}  # normalized to lowercase
    assert result.location == "Paris"


# ---------------------------------------------------------------------------
# JSON format errors
# ---------------------------------------------------------------------------


async def test_extract_invalid_json() -> None:
    gateway = _make_gateway("this is not json {{{")

    with pytest.raises(LLMResponseFormatError) as exc_info:
        await gateway.extract_profile_from_cv("some cv text")

    assert "invalid JSON" in exc_info.value.reason


async def test_extract_missing_required_field() -> None:
    data = json.loads(_VALID_JSON)
    del data["email"]
    gateway = _make_gateway(json.dumps(data))

    with pytest.raises(LLMResponseFormatError):
        await gateway.extract_profile_from_cv("some cv text")


# ---------------------------------------------------------------------------
# Optional field edge cases
# ---------------------------------------------------------------------------


async def test_extract_empty_skills() -> None:
    data = json.loads(_VALID_JSON)
    data["skills"] = []
    gateway = _make_gateway(json.dumps(data))

    result = await gateway.extract_profile_from_cv("some cv text")

    assert result.skills == ()


async def test_extract_null_location() -> None:
    data = json.loads(_VALID_JSON)
    data["location"] = None
    gateway = _make_gateway(json.dumps(data))

    result = await gateway.extract_profile_from_cv("some cv text")

    assert result.location is None


async def test_extract_null_optional_fields_use_defaults() -> None:
    data = json.loads(_VALID_JSON)
    data["years_experience"] = None
    data["preferred_contract_type"] = None
    data["target_tjm"] = None
    data["preferred_remote_mode"] = None
    gateway = _make_gateway(json.dumps(data))

    result = await gateway.extract_profile_from_cv("some cv text")

    assert result.years_experience == 0
    assert result.preferred_contract_type == "unknown"
    assert result.target_tjm == 0.0
    assert result.preferred_remote_mode == "unknown"


# ---------------------------------------------------------------------------
# Availability parsing
# ---------------------------------------------------------------------------


async def test_extract_availability_immediate() -> None:
    data = json.loads(_VALID_JSON)
    data["availability"] = "immediate"
    gateway = _make_gateway(json.dumps(data))

    before = datetime.now(UTC)
    result = await gateway.extract_profile_from_cv("some cv text")
    after = datetime.now(UTC)

    assert before <= result.availability <= after


async def test_extract_availability_iso_date() -> None:
    data = json.loads(_VALID_JSON)
    data["availability"] = "2024-09-01"
    gateway = _make_gateway(json.dumps(data))

    result = await gateway.extract_profile_from_cv("some cv text")

    assert result.availability.date() == date(2024, 9, 1)


# ---------------------------------------------------------------------------
# API error
# ---------------------------------------------------------------------------


async def test_api_error_raises_llm_extraction_error() -> None:
    gateway = GroqLLMGateway(api_key="fake", _client=_ErrorGroqClient())

    with pytest.raises(LLMExtractionError) as exc_info:
        await gateway.extract_profile_from_cv("some cv text")

    assert "Groq API unavailable" in exc_info.value.reason


# ---------------------------------------------------------------------------
# generate_search_queries — setup
# ---------------------------------------------------------------------------

_VALID_SEARCH_QUERIES_JSON = json.dumps({
    "queries": [
        {"query": "symfony freelance paris", "source": "linkedin", "limit": 50},
        {"query": "php freelance france", "source": "linkedin", "limit": 50},
    ]
})


def _make_profile() -> UserProfile:
    return UserProfile(
        id=uuid4(),
        email="ada@example.com",
        full_name="Ada Lovelace",
        title="Symfony Expert",
        years_experience=10,
        preferred_contract_type=ContractType.FREELANCE,
        target_tjm=700.0,
        preferred_remote_mode=RemoteMode.HYBRID,
        skills=Stack(("symfony", "php", "mysql")),
        availability=datetime.now(UTC),
        location="Paris",
        cv_raw_text="Symfony developer with 10 years of experience...",
    )


# ---------------------------------------------------------------------------
# generate_search_queries — nominal
# ---------------------------------------------------------------------------


async def test_generate_search_queries_returns_list_of_dicts() -> None:
    gateway = _make_gateway(_VALID_SEARCH_QUERIES_JSON)
    result = await gateway.generate_search_queries(_make_profile())
    assert isinstance(result, list)
    assert all(isinstance(q, dict) for q in result)


async def test_generate_search_queries_has_expected_keys() -> None:
    gateway = _make_gateway(_VALID_SEARCH_QUERIES_JSON)
    result = await gateway.generate_search_queries(_make_profile())
    assert result[0]["query"] == "symfony freelance paris"
    assert result[0]["source"] == "linkedin"
    assert result[0]["limit"] == 50


async def test_generate_search_queries_returns_all_items() -> None:
    gateway = _make_gateway(_VALID_SEARCH_QUERIES_JSON)
    result = await gateway.generate_search_queries(_make_profile())
    assert len(result) == 2


# ---------------------------------------------------------------------------
# generate_search_queries — errors
# ---------------------------------------------------------------------------


async def test_generate_search_queries_invalid_json_raises_format_error() -> None:
    gateway = _make_gateway("not json {{{")
    with pytest.raises(LLMResponseFormatError):
        await gateway.generate_search_queries(_make_profile())


async def test_generate_search_queries_missing_queries_key_raises_format_error() -> None:
    gateway = _make_gateway(json.dumps({"result": []}))
    with pytest.raises(LLMResponseFormatError):
        await gateway.generate_search_queries(_make_profile())


async def test_generate_search_queries_api_error_raises_extraction_error() -> None:
    gateway = GroqLLMGateway(api_key="fake", _client=_ErrorGroqClient())
    with pytest.raises(LLMExtractionError):
        await gateway.generate_search_queries(_make_profile())


# ---------------------------------------------------------------------------
# analyze_post — setup
# ---------------------------------------------------------------------------

_VALID_ANALYZE_POST_JSON = json.dumps({
    "is_job_offer": True,
    "title": "Mission Freelance Python",
    "company": "Acme Corp",
    "location": "Paris",
    "contract_type": "freelance",
    "summary": "Mission backend Python/FastAPI pour une startup fintech.",
    "required_skills": ["Python", "FastAPI"],
    "nice_to_have_skills": ["Docker"],
    "seniority": "senior",
    "remote_policy": "full remote",
    "daily_rate": "650€/j",
})


def _make_raw_post() -> RawPost:
    return RawPost(
        source="linkedin",
        external_id="post-123",
        author_name="Jean Dupont",
        author_url="https://linkedin.com/in/jean-dupont",
        content="Nous cherchons un développeur Python senior pour une mission freelance.",
        post_url="https://linkedin.com/posts/123",
        published_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        scraped_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
    )


# ---------------------------------------------------------------------------
# analyze_post — nominal
# ---------------------------------------------------------------------------


async def test_analyze_post_returns_post_analysis() -> None:
    gateway = _make_gateway(_VALID_ANALYZE_POST_JSON)

    result = await gateway.analyze_post(_make_raw_post())

    assert isinstance(result, PostAnalysis)
    assert result.is_job_offer is True
    assert result.title == "Mission Freelance Python"
    assert result.company == "Acme Corp"
    assert result.summary == "Mission backend Python/FastAPI pour une startup fintech."
    assert "Python" in result.required_skills
    assert "FastAPI" in result.required_skills
    assert "Docker" in result.nice_to_have_skills
    assert result.daily_rate == "650€/j"
    assert result.remote_policy == "full remote"


async def test_analyze_post_is_job_offer_false() -> None:
    payload = json.dumps({
        "is_job_offer": False,
        "summary": "Post de partage de contenu, pas une offre.",
        "required_skills": [],
        "nice_to_have_skills": [],
    })
    gateway = _make_gateway(payload)

    result = await gateway.analyze_post(_make_raw_post())

    assert result.is_job_offer is False


async def test_analyze_post_is_job_offer_absent_defaults_false() -> None:
    payload = json.dumps({
        "summary": "Mission Python.",
        "required_skills": [],
        "nice_to_have_skills": [],
    })
    gateway = _make_gateway(payload)

    result = await gateway.analyze_post(_make_raw_post())

    assert result.is_job_offer is False


async def test_analyze_post_missing_optional_fields_uses_defaults() -> None:
    minimal = json.dumps({
        "summary": "Mission Python.",
        "required_skills": [],
        "nice_to_have_skills": [],
    })
    gateway = _make_gateway(minimal)

    result = await gateway.analyze_post(_make_raw_post())

    assert result.title is None
    assert result.company is None
    assert result.location is None
    assert result.daily_rate is None
    assert result.required_skills == ()
    assert result.nice_to_have_skills == ()


async def test_analyze_post_null_fields_become_none() -> None:
    data = json.loads(_VALID_ANALYZE_POST_JSON)
    data["title"] = None
    data["company"] = None
    data["daily_rate"] = None
    gateway = _make_gateway(json.dumps(data))

    result = await gateway.analyze_post(_make_raw_post())

    assert result.title is None
    assert result.company is None
    assert result.daily_rate is None


# ---------------------------------------------------------------------------
# analyze_post — errors
# ---------------------------------------------------------------------------


async def test_analyze_post_invalid_json_raises_parsing_error() -> None:
    gateway = _make_gateway("not json {{{")

    with pytest.raises(AnalyzePostParsingError) as exc_info:
        await gateway.analyze_post(_make_raw_post())

    assert "invalid JSON" in exc_info.value.reason


async def test_analyze_post_empty_summary_raises_domain_error() -> None:
    data = json.loads(_VALID_ANALYZE_POST_JSON)
    data["summary"] = ""
    gateway = _make_gateway(json.dumps(data))

    with pytest.raises(EmptyAnalysisSummaryError):
        await gateway.analyze_post(_make_raw_post())


async def test_analyze_post_api_error_raises_extraction_error() -> None:
    gateway = GroqLLMGateway(api_key="fake", _client=_ErrorGroqClient())

    with pytest.raises(LLMExtractionError) as exc_info:
        await gateway.analyze_post(_make_raw_post())

    assert "Groq API unavailable" in exc_info.value.reason


# ---------------------------------------------------------------------------
# analyze_post — strict json_schema mode (constrained decoding)
# ---------------------------------------------------------------------------


async def test_analyze_post_strict_mode_sends_json_schema_response_format() -> None:
    client = _FakeGroqClient(_VALID_ANALYZE_POST_JSON)
    gateway = GroqLLMGateway(
        api_key="fake",
        model="openai/gpt-oss-20b",
        _client=client,
        strict_json_schema=True,
    )

    await gateway.analyze_post(_make_raw_post())

    assert client.create_calls[0]["response_format"] == ANALYZE_POST_JSON_SCHEMA


async def test_analyze_post_default_mode_still_sends_json_object() -> None:
    client = _FakeGroqClient(_VALID_ANALYZE_POST_JSON)
    gateway = GroqLLMGateway(api_key="fake", _client=client)

    await gateway.analyze_post(_make_raw_post())

    assert client.create_calls[0]["response_format"] == {"type": "json_object"}


def test_strict_json_schema_with_unsupported_model_raises_value_error() -> None:
    with pytest.raises(ValueError, match="strict_json_schema=True requires a model"):
        GroqLLMGateway(
            api_key="fake",
            model="llama-3.3-70b-versatile",
            strict_json_schema=True,
        )


async def test_strict_json_schema_with_gpt_oss_120b_is_accepted() -> None:
    client = _FakeGroqClient(_VALID_ANALYZE_POST_JSON)
    gateway = GroqLLMGateway(
        api_key="fake",
        model="openai/gpt-oss-120b",
        _client=client,
        strict_json_schema=True,
    )

    await gateway.analyze_post(_make_raw_post())

    assert client.create_calls[0]["response_format"] == ANALYZE_POST_JSON_SCHEMA


# ---------------------------------------------------------------------------
# summarize_mission — nominal
# ---------------------------------------------------------------------------


async def test_summarize_mission_returns_content() -> None:
    gateway = _make_gateway("Mission Python freelance, 3 mois, remote.")

    result = await gateway.summarize_mission("Nous recherchons un développeur Python...")

    assert result == "Mission Python freelance, 3 mois, remote."


async def test_summarize_mission_does_not_send_response_format() -> None:
    client = _FakeGroqClient("summary text")
    gateway = GroqLLMGateway(api_key="fake", _client=client)

    await gateway.summarize_mission("some content")

    assert "response_format" not in client.create_calls[0]


# ---------------------------------------------------------------------------
# LLMTracer integration
# ---------------------------------------------------------------------------


async def test_extract_profile_from_cv_calls_tracer_with_correct_messages() -> None:
    from src.Infrastructure.External.LLM.groq_llm_gateway import _load_prompt

    tracer = _SpyTracer()
    gateway = GroqLLMGateway(api_key="fake", _client=_FakeGroqClient(_VALID_JSON), tracer=tracer)
    system_prompt = _load_prompt("cv_profile_extraction.txt")

    await gateway.extract_profile_from_cv("some cv text")

    assert len(tracer.start_completion_calls) == 1
    call = tracer.start_completion_calls[0]
    assert call["name"] == "extract_profile_from_cv"
    assert call["provider"] == "groq"
    assert call["prompt_version"] == "v1"
    assert call["system_prompt"] == system_prompt
    assert call["messages"] == [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "some cv text"},
    ]
    assert tracer.handle_calls == [
        {
            "event": "succeed",
            "trace_name": "extract_profile_from_cv",
            "output": _VALID_JSON,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
        }
    ]


async def test_summarize_mission_calls_tracer_with_no_system_prompt() -> None:
    tracer = _SpyTracer()
    gateway = GroqLLMGateway(api_key="fake", _client=_FakeGroqClient("a summary"), tracer=tracer)

    await gateway.summarize_mission("some content")

    call = tracer.start_completion_calls[0]
    assert call["name"] == "summarize_mission"
    assert call["system_prompt"] is None
    assert tracer.handle_calls[0]["event"] == "succeed"
    assert tracer.handle_calls[0]["output"] == "a summary"


async def test_generate_search_queries_calls_tracer_with_correct_messages() -> None:
    from src.Infrastructure.External.LLM.groq_llm_gateway import _load_prompt

    tracer = _SpyTracer()
    gateway = GroqLLMGateway(
        api_key="fake", _client=_FakeGroqClient(_VALID_SEARCH_QUERIES_JSON), tracer=tracer
    )
    system_prompt = _load_prompt("search_query_generation.txt")

    await gateway.generate_search_queries(_make_profile())

    call = tracer.start_completion_calls[0]
    assert call["name"] == "generate_search_queries"
    assert call["system_prompt"] == system_prompt
    assert call["messages"][0] == {"role": "system", "content": system_prompt}


async def test_analyze_post_calls_tracer_with_no_system_prompt() -> None:
    tracer = _SpyTracer()
    gateway = GroqLLMGateway(
        api_key="fake", _client=_FakeGroqClient(_VALID_ANALYZE_POST_JSON), tracer=tracer
    )

    await gateway.analyze_post(_make_raw_post())

    call = tracer.start_completion_calls[0]
    assert call["name"] == "analyze_post"
    assert call["system_prompt"] is None
    assert len(call["messages"]) == 1
    assert call["messages"][0]["role"] == "user"


async def test_extract_profile_from_cv_traces_error_on_client_exception() -> None:
    tracer = _SpyTracer()
    gateway = GroqLLMGateway(api_key="fake", _client=_ErrorGroqClient(), tracer=tracer)

    with pytest.raises(LLMExtractionError):
        await gateway.extract_profile_from_cv("some cv text")

    assert len(tracer.handle_calls) == 1
    fail_call = tracer.handle_calls[0]
    assert fail_call["event"] == "fail"
    assert fail_call["trace_name"] == "extract_profile_from_cv"
    assert isinstance(fail_call["error"], RuntimeError)
    assert "Groq API unavailable" in str(fail_call["error"])


async def test_default_tracer_is_null_tracer_when_not_provided() -> None:
    gateway = GroqLLMGateway(api_key="fake", _client=_FakeGroqClient(_VALID_JSON))

    result = await gateway.extract_profile_from_cv("some cv text")

    assert isinstance(result, CVProfile)


async def test_token_usage_missing_from_response_does_not_raise() -> None:
    tracer = _SpyTracer()
    gateway = GroqLLMGateway(api_key="fake", _client=_FakeGroqClient(_VALID_JSON), tracer=tracer)

    await gateway.extract_profile_from_cv("some cv text")

    succeed_call = tracer.handle_calls[0]
    assert succeed_call["input_tokens"] is None
    assert succeed_call["output_tokens"] is None
    assert succeed_call["total_tokens"] is None


async def test_token_usage_present_is_forwarded_to_tracer() -> None:
    usage = types.SimpleNamespace(prompt_tokens=120, completion_tokens=45, total_tokens=165)
    tracer = _SpyTracer()
    client = _FakeGroqClient(_VALID_JSON, usage=usage)
    gateway = GroqLLMGateway(api_key="fake", _client=client, tracer=tracer)

    await gateway.extract_profile_from_cv("some cv text")

    succeed_call = tracer.handle_calls[0]
    assert succeed_call["input_tokens"] == 120
    assert succeed_call["output_tokens"] == 45
    assert succeed_call["total_tokens"] == 165
