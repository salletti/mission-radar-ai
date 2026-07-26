"""Unit tests for SaveProfile use case — no I/O, no DB, no external services."""
from datetime import datetime, timezone
from typing import Optional, Union
from uuid import UUID, uuid4


from src.Application.DTO.cv_profile import CVProfile
from src.Application.DTO.save_profile_command import SaveProfileCommand
from src.Application.DTO.save_profile_result import SaveProfileResult
from src.Application.Gateway.embedding_gateway import EmbeddingGateway
from src.Application.Gateway.llm_gateway import LLMGateway
from src.Application.UseCase.save_profile import SaveProfile
from src.Domain.Entity.search_query import SearchQuery
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Repository.search_query_repository import SearchQueryRepository
from src.Domain.Repository.user_profile_repository import UserProfileRepository
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack
from src.Infrastructure.External.LLM.exceptions import LLMExtractionError, LLMResponseFormatError

_AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)

_FAKE_PROFILE_DTO = CVProfile(
    email="ada@example.com",
    full_name="Ada Lovelace",
    title="Senior Python Engineer",
    years_experience=10,
    preferred_contract_type="freelance",
    target_tjm=700.0,
    preferred_remote_mode="full_remote",
    skills=("python", "fastapi"),
    availability=_AVAILABILITY,
    location="Paris",
)

_FAKE_CV_RAW_TEXT = "Ada Lovelace — Senior Python Engineer..."

_FAKE_EMBEDDING = [0.1] * 384


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeUserProfileRepository(UserProfileRepository):
    def __init__(self, existing: Optional[UserProfile] = None) -> None:
        self._existing = existing
        self.saved: list[UserProfile] = []

    async def save(self, profile: UserProfile) -> None:
        self.saved.append(profile)

    async def get_by_id(self, profile_id: UUID) -> Optional[UserProfile]:
        if self._existing and self._existing.id == profile_id:
            return self._existing
        return None

    async def get_by_email(self, email: str) -> Optional[UserProfile]:
        if self._existing and self._existing.email == email:
            return self._existing
        return None

    async def get_active_profile(self) -> Optional[UserProfile]:
        return self._existing

    async def delete(self, profile_id: UUID) -> None:
        pass


class FakeEmbeddingGateway(EmbeddingGateway):
    def __init__(self) -> None:
        self.embed_calls: list[str] = []

    async def embed_text(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return _FAKE_EMBEDDING

    async def compute_similarity(self, a: list[float], b: list[float]) -> float:
        return 1.0


class FakeLLMGateway(LLMGateway):
    """Stub LLM gateway — returns a fixed list[dict] or raises a configured exception."""

    def __init__(
        self,
        search_query_response: Union[list[dict], Exception, None] = None,
    ) -> None:
        self._response: Union[list[dict], Exception] = (
            search_query_response
            if search_query_response is not None
            else [{"query": "python engineer freelance paris", "source": "linkedin", "limit": 50}]
        )

    async def extract_profile_from_cv(self, cv_text: str) -> CVProfile:  # type: ignore[override]
        raise NotImplementedError

    async def summarize_mission(self, content: str) -> str:
        return ""

    async def generate_search_queries(self, profile: UserProfile) -> list[dict]:
        if isinstance(self._response, Exception):
            raise self._response
        return self._response

    async def analyze_post(self, raw_post) -> "PostAnalysis":  # type: ignore[override]
        raise NotImplementedError


class FakeSearchQueryRepository(SearchQueryRepository):
    def __init__(self) -> None:
        self.saved: list[SearchQuery] = []
        self.deleted_for: list[UUID] = []

    async def save_many(self, queries: list[SearchQuery]) -> None:
        self.saved.extend(queries)

    async def delete_by_profile(self, user_profile_id: UUID) -> None:
        self.deleted_for.append(user_profile_id)

    async def get_by_profile(self, user_profile_id: UUID) -> list[SearchQuery]:
        return [q for q in self.saved if q.user_profile_id == user_profile_id]

    async def get_by_source(self, source: str) -> list[SearchQuery]:
        return [q for q in self.saved if q.source == source]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _make_use_case(
    existing: Optional[UserProfile] = None,
    llm: Optional[FakeLLMGateway] = None,
) -> tuple[SaveProfile, FakeUserProfileRepository, FakeEmbeddingGateway, FakeSearchQueryRepository]:
    repo = FakeUserProfileRepository(existing=existing)
    embedding = FakeEmbeddingGateway()
    search_query_repo = FakeSearchQueryRepository()
    uc = SaveProfile(
        user_profile_repo=repo,
        embedding_gateway=embedding,
        search_query_repo=search_query_repo,
        llm_gateway=llm or FakeLLMGateway(),
    )
    return uc, repo, embedding, search_query_repo


def _make_command(
    email: str = "ada@example.com",
    cv_raw_text: str = _FAKE_CV_RAW_TEXT,
) -> SaveProfileCommand:
    dto = CVProfile(
        email=email,
        full_name=_FAKE_PROFILE_DTO.full_name,
        title=_FAKE_PROFILE_DTO.title,
        years_experience=_FAKE_PROFILE_DTO.years_experience,
        preferred_contract_type=_FAKE_PROFILE_DTO.preferred_contract_type,
        target_tjm=_FAKE_PROFILE_DTO.target_tjm,
        preferred_remote_mode=_FAKE_PROFILE_DTO.preferred_remote_mode,
        skills=_FAKE_PROFILE_DTO.skills,
        availability=_AVAILABILITY,
        location=_FAKE_PROFILE_DTO.location,
    )
    return SaveProfileCommand(cv_profile=dto, cv_raw_text=cv_raw_text)


def _make_existing_profile(email: str = "ada@example.com") -> UserProfile:
    return UserProfile(
        id=uuid4(),
        email=email,
        full_name="Old Name",
        title="Old Title",
        years_experience=5,
        preferred_contract_type=ContractType.FREELANCE,
        target_tjm=500.0,
        preferred_remote_mode=RemoteMode.ONSITE,
        skills=Stack(("php",)),
        availability=_AVAILABILITY,
    )


# ---------------------------------------------------------------------------
# Tests — new profile
# ---------------------------------------------------------------------------


async def test_save_profile_returns_result() -> None:
    uc, _, _, _ = _make_use_case()
    result = await uc.execute(_make_command())
    assert isinstance(result, SaveProfileResult)


async def test_save_profile_status_created_for_new_email() -> None:
    uc, _, _, _ = _make_use_case()
    result = await uc.execute(_make_command())
    assert result.status == "created"


async def test_save_profile_result_contains_email() -> None:
    uc, _, _, _ = _make_use_case()
    result = await uc.execute(_make_command())
    assert result.email == "ada@example.com"


async def test_save_profile_result_contains_profile_id() -> None:
    uc, _, _, _ = _make_use_case()
    result = await uc.execute(_make_command())
    assert isinstance(result.profile_id, UUID)


async def test_save_profile_calls_repo_save() -> None:
    uc, repo, _, _ = _make_use_case()
    await uc.execute(_make_command())
    assert len(repo.saved) == 1


async def test_save_profile_stores_embedding_on_profile() -> None:
    uc, repo, _, _ = _make_use_case()
    await uc.execute(_make_command())
    assert repo.saved[0].embedding == _FAKE_EMBEDDING


async def test_save_profile_stores_cv_raw_text_on_profile() -> None:
    uc, repo, _, _ = _make_use_case()
    await uc.execute(_make_command())
    assert repo.saved[0].cv_raw_text == _FAKE_CV_RAW_TEXT


async def test_save_profile_calls_embed_text_once() -> None:
    uc, _, embedding, _ = _make_use_case()
    await uc.execute(_make_command())
    assert len(embedding.embed_calls) == 1


async def test_save_profile_embed_text_contains_title() -> None:
    uc, _, embedding, _ = _make_use_case()
    await uc.execute(_make_command())
    assert "Senior Python Engineer" in embedding.embed_calls[0]


async def test_save_profile_embed_text_contains_cv_raw_text() -> None:
    uc, _, embedding, _ = _make_use_case()
    await uc.execute(_make_command(cv_raw_text="raw cv content here"))
    assert "raw cv content here" in embedding.embed_calls[0]


# ---------------------------------------------------------------------------
# Tests — existing profile (update)
# ---------------------------------------------------------------------------


async def test_save_profile_status_updated_for_existing_email() -> None:
    existing = _make_existing_profile()
    uc, _, _, _ = _make_use_case(existing=existing)
    result = await uc.execute(_make_command(email=existing.email))
    assert result.status == "updated"


async def test_save_profile_preserves_id_on_update() -> None:
    existing = _make_existing_profile()
    uc, repo, _, _ = _make_use_case(existing=existing)
    result = await uc.execute(_make_command(email=existing.email))
    assert result.profile_id == existing.id
    assert repo.saved[0].id == existing.id


async def test_save_profile_updates_skills_on_update() -> None:
    existing = _make_existing_profile()
    uc, repo, _, _ = _make_use_case(existing=existing)
    await uc.execute(_make_command(email=existing.email))
    updated_skills = set(repo.saved[0].skills.technologies)
    assert "python" in updated_skills
    assert "fastapi" in updated_skills


# ---------------------------------------------------------------------------
# Tests — search queries (orchestration)
# ---------------------------------------------------------------------------


async def test_save_profile_search_queries_count_nonzero() -> None:
    uc, _, _, _ = _make_use_case()
    result = await uc.execute(_make_command())
    assert result.search_queries_count > 0


async def test_save_profile_search_queries_count_matches_saved() -> None:
    uc, _, _, sq_repo = _make_use_case()
    result = await uc.execute(_make_command())
    assert result.search_queries_count == len(sq_repo.saved)


async def test_save_profile_delete_called_before_save() -> None:
    uc, _, _, sq_repo = _make_use_case()
    await uc.execute(_make_command())
    assert len(sq_repo.deleted_for) == 1


async def test_save_profile_delete_called_with_profile_id() -> None:
    uc, _, _, sq_repo = _make_use_case()
    result = await uc.execute(_make_command())
    assert sq_repo.deleted_for[0] == result.profile_id


async def test_save_profile_delete_called_on_update() -> None:
    existing = _make_existing_profile()
    uc, _, _, sq_repo = _make_use_case(existing=existing)
    await uc.execute(_make_command(email=existing.email))
    assert len(sq_repo.deleted_for) == 1
    assert sq_repo.deleted_for[0] == existing.id


async def test_save_profile_queries_linked_to_profile() -> None:
    uc, _, _, sq_repo = _make_use_case()
    result = await uc.execute(_make_command())
    assert all(q.user_profile_id == result.profile_id for q in sq_repo.saved)


# ---------------------------------------------------------------------------
# Tests — LLM query generation (happy path)
# ---------------------------------------------------------------------------


async def test_save_profile_llm_queries_persisted() -> None:
    llm_response = [
        {"query": "ai engineer freelance paris", "source": "linkedin", "limit": 50},
        {"query": "llm engineer france", "source": "linkedin", "limit": 50},
        {"query": "python freelance paris", "source": "linkedin", "limit": 50},
    ]
    uc, _, _, sq_repo = _make_use_case(llm=FakeLLMGateway(llm_response))
    await uc.execute(_make_command())
    assert len(sq_repo.saved) == 3
    assert sq_repo.saved[0].query == "ai engineer freelance paris"


async def test_save_profile_llm_queries_source_and_limit() -> None:
    llm_response = [{"query": "symfony freelance paris", "source": "linkedin", "limit": 50}]
    uc, _, _, sq_repo = _make_use_case(llm=FakeLLMGateway(llm_response))
    await uc.execute(_make_command())
    assert sq_repo.saved[0].source == "linkedin"
    assert sq_repo.saved[0].limit == 50


async def test_save_profile_llm_queries_linked_to_profile() -> None:
    llm_response = [
        {"query": "ai engineer freelance paris", "source": "linkedin", "limit": 50},
    ]
    uc, _, _, sq_repo = _make_use_case(llm=FakeLLMGateway(llm_response))
    result = await uc.execute(_make_command())
    assert all(q.user_profile_id == result.profile_id for q in sq_repo.saved)


# ---------------------------------------------------------------------------
# Tests — LLM fallback
# ---------------------------------------------------------------------------


async def test_save_profile_llm_extraction_error_triggers_fallback() -> None:
    uc, _, _, sq_repo = _make_use_case(llm=FakeLLMGateway(LLMExtractionError(reason="timeout")))
    await uc.execute(_make_command())
    assert len(sq_repo.saved) >= 1


async def test_save_profile_llm_format_error_triggers_fallback() -> None:
    uc, _, _, sq_repo = _make_use_case(llm=FakeLLMGateway(LLMResponseFormatError(reason="bad json")))
    await uc.execute(_make_command())
    assert len(sq_repo.saved) >= 1


async def test_save_profile_generic_exception_triggers_fallback() -> None:
    uc, _, _, sq_repo = _make_use_case(llm=FakeLLMGateway(RuntimeError("unexpected")))
    await uc.execute(_make_command())
    assert len(sq_repo.saved) >= 1


async def test_save_profile_empty_llm_response_triggers_fallback() -> None:
    uc, _, _, sq_repo = _make_use_case(llm=FakeLLMGateway([]))
    await uc.execute(_make_command())
    assert len(sq_repo.saved) >= 1


async def test_save_profile_fallback_queries_linked_to_profile() -> None:
    uc, _, _, sq_repo = _make_use_case(llm=FakeLLMGateway(LLMExtractionError(reason="down")))
    result = await uc.execute(_make_command())
    assert all(q.user_profile_id == result.profile_id for q in sq_repo.saved)


# ---------------------------------------------------------------------------
# Tests — deduplication and cap
# ---------------------------------------------------------------------------


async def test_save_profile_duplicate_queries_deduplicated() -> None:
    llm_response = [
        {"query": "ai engineer freelance paris", "source": "linkedin", "limit": 50},
        {"query": "ai engineer freelance paris", "source": "linkedin", "limit": 50},
        {"query": "llm engineer france", "source": "linkedin", "limit": 50},
    ]
    uc, _, _, sq_repo = _make_use_case(llm=FakeLLMGateway(llm_response))
    await uc.execute(_make_command())
    queries_str = [q.query for q in sq_repo.saved]
    assert queries_str.count("ai engineer freelance paris") == 1
    assert len(sq_repo.saved) == 2


async def test_save_profile_queries_capped_at_five() -> None:
    llm_response = [
        {"query": f"tech{i} freelance paris", "source": "linkedin", "limit": 50}
        for i in range(8)
    ]
    uc, _, _, sq_repo = _make_use_case(llm=FakeLLMGateway(llm_response))
    await uc.execute(_make_command())
    assert len(sq_repo.saved) == 5


async def test_save_profile_empty_query_string_skipped() -> None:
    llm_response = [
        {"query": "", "source": "linkedin", "limit": 50},
        {"query": "ai engineer paris", "source": "linkedin", "limit": 50},
    ]
    uc, _, _, sq_repo = _make_use_case(llm=FakeLLMGateway(llm_response))
    await uc.execute(_make_command())
    assert len(sq_repo.saved) == 1
    assert sq_repo.saved[0].query == "ai engineer paris"


async def test_save_profile_whitespace_query_skipped() -> None:
    llm_response = [
        {"query": "   ", "source": "linkedin", "limit": 50},
        {"query": "llm engineer france", "source": "linkedin", "limit": 50},
    ]
    uc, _, _, sq_repo = _make_use_case(llm=FakeLLMGateway(llm_response))
    await uc.execute(_make_command())
    assert len(sq_repo.saved) == 1
    assert sq_repo.saved[0].query == "llm engineer france"
