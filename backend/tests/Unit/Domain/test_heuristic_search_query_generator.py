"""Unit tests for HeuristicSearchQueryGenerator Domain Service — pure, no I/O."""
from datetime import datetime, timezone
from uuid import uuid4


from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Service.heuristic_search_query_generator import HeuristicSearchQueryGenerator, _MAX_QUERIES
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack

_AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_profile(
    title: str = "Python Developer",
    skills: tuple[str, ...] = ("python",),
    location: str | None = "Paris",
    contract_type: ContractType = ContractType.FREELANCE,
) -> UserProfile:
    return UserProfile(
        id=uuid4(),
        email="dev@example.com",
        full_name="Dev Test",
        title=title,
        years_experience=5,
        preferred_contract_type=contract_type,
        target_tjm=600.0,
        preferred_remote_mode=RemoteMode.FULL_REMOTE,
        skills=Stack(skills),
        availability=_AVAILABILITY,
        location=location,
    )


def _svc() -> HeuristicSearchQueryGenerator:
    return HeuristicSearchQueryGenerator()


# ---------------------------------------------------------------------------
# Tests — profil Python
# ---------------------------------------------------------------------------


async def test_python_profile_generates_title_query() -> None:
    profile = _make_profile(title="Python Engineer", skills=("fastapi", "python"), location="Paris")
    queries = _svc().generate(profile)
    query_strings = [q.query for q in queries]
    assert "python engineer freelance paris" in query_strings


async def test_python_profile_generates_skill_queries() -> None:
    profile = _make_profile(title="Python Engineer", skills=("fastapi", "python"), location="Paris")
    queries = _svc().generate(profile)
    query_strings = [q.query for q in queries]
    assert "fastapi freelance paris" in query_strings
    assert "python freelance paris" in query_strings


async def test_python_profile_query_count() -> None:
    profile = _make_profile(title="Python Engineer", skills=("fastapi", "python"), location="Paris")
    queries = _svc().generate(profile)
    assert len(queries) == 3


# ---------------------------------------------------------------------------
# Tests — profil Symfony
# ---------------------------------------------------------------------------


async def test_symfony_profile_title_query() -> None:
    profile = _make_profile(title="Symfony Developer", skills=("doctrine", "php", "symfony"), location="Lyon")
    queries = _svc().generate(profile)
    query_strings = [q.query for q in queries]
    assert "symfony developer freelance lyon" in query_strings


async def test_symfony_profile_skill_queries() -> None:
    profile = _make_profile(title="Symfony Developer", skills=("doctrine", "php", "symfony"), location="Lyon")
    queries = _svc().generate(profile)
    query_strings = [q.query for q in queries]
    assert "doctrine freelance lyon" in query_strings
    assert "php freelance lyon" in query_strings
    assert "symfony freelance lyon" in query_strings


# ---------------------------------------------------------------------------
# Tests — profil AI
# ---------------------------------------------------------------------------


async def test_ai_profile_generates_expected_queries() -> None:
    profile = _make_profile(title="AI Engineer", skills=("langchain", "openai", "rag"), location="Paris")
    queries = _svc().generate(profile)
    query_strings = [q.query for q in queries]
    assert "ai engineer freelance paris" in query_strings
    assert "langchain freelance paris" in query_strings
    assert "openai freelance paris" in query_strings
    assert "rag freelance paris" in query_strings


# ---------------------------------------------------------------------------
# Tests — profil sans localisation
# ---------------------------------------------------------------------------


async def test_no_location_queries_have_no_city() -> None:
    profile = _make_profile(title="Python Developer", skills=("python",), location=None)
    queries = _svc().generate(profile)
    for q in queries:
        assert "paris" not in q.query
        assert "lyon" not in q.query


async def test_no_location_title_query() -> None:
    profile = _make_profile(title="Python Developer", skills=("python",), location=None)
    queries = _svc().generate(profile)
    assert queries[0].query == "python developer freelance"


async def test_no_location_skill_query() -> None:
    profile = _make_profile(title="Python Developer", skills=("python",), location=None)
    queries = _svc().generate(profile)
    query_strings = [q.query for q in queries]
    assert "python freelance" in query_strings


# ---------------------------------------------------------------------------
# Tests — profil sans stack
# ---------------------------------------------------------------------------


async def test_no_skills_generates_one_query() -> None:
    profile = _make_profile(title="Senior Developer", skills=(), location="Paris")
    queries = _svc().generate(profile)
    assert len(queries) == 1


async def test_no_skills_query_is_from_title() -> None:
    profile = _make_profile(title="Senior Developer", skills=(), location="Paris")
    queries = _svc().generate(profile)
    assert queries[0].query == "senior developer freelance paris"


# ---------------------------------------------------------------------------
# Tests — cap MAX_QUERIES
# ---------------------------------------------------------------------------


async def test_max_queries_cap_with_many_skills() -> None:
    many_skills = ("django", "fastapi", "flask", "graphql", "langchain", "openai", "python", "rag", "react", "vue")
    profile = _make_profile(title="Fullstack Dev", skills=many_skills, location="Paris")
    queries = _svc().generate(profile)
    assert len(queries) == _MAX_QUERIES


# ---------------------------------------------------------------------------
# Tests — déduplication
# ---------------------------------------------------------------------------


async def test_deduplication_title_matches_skill() -> None:
    profile = _make_profile(title="python", skills=("fastapi", "python"), location="Paris")
    queries = _svc().generate(profile)
    query_strings = [q.query for q in queries]
    assert query_strings.count("python freelance paris") == 1


async def test_deduplication_total_count_reduced() -> None:
    profile = _make_profile(title="python", skills=("fastapi", "python"), location="Paris")
    queries = _svc().generate(profile)
    assert len(queries) == 2


# ---------------------------------------------------------------------------
# Tests — contrat non-freelance
# ---------------------------------------------------------------------------


async def test_non_freelance_contract_no_freelance_keyword() -> None:
    profile = _make_profile(
        title="Java Developer",
        skills=("java", "spring"),
        location="Paris",
        contract_type=ContractType.PERMANENT,
    )
    queries = _svc().generate(profile)
    for q in queries:
        assert "freelance" not in q.query


async def test_non_freelance_contract_location_still_present() -> None:
    profile = _make_profile(
        title="Java Developer",
        skills=("java",),
        location="Paris",
        contract_type=ContractType.PERMANENT,
    )
    queries = _svc().generate(profile)
    assert queries[0].query == "java developer paris"


# ---------------------------------------------------------------------------
# Tests — métadonnées SearchQuery
# ---------------------------------------------------------------------------


async def test_search_query_source_is_linkedin() -> None:
    profile = _make_profile()
    queries = _svc().generate(profile)
    assert all(q.source == "linkedin" for q in queries)


async def test_search_query_limit_is_fifty() -> None:
    profile = _make_profile()
    queries = _svc().generate(profile)
    assert all(q.limit == 50 for q in queries)


async def test_search_query_user_profile_id_matches_profile() -> None:
    profile = _make_profile()
    queries = _svc().generate(profile)
    assert all(q.user_profile_id == profile.id for q in queries)
