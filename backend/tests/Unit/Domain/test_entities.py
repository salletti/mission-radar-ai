from datetime import datetime, timezone

import pytest

from src.Domain.Entity.analyzed_post import AnalyzedPost
from src.Domain.Entity.raw_post import RawPost
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Exception.domain_exceptions import (
    EmptyAnalysisSummaryError,
    EmptyPostContentError,
    InvalidEmailError,
)
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _raw_post(**kwargs) -> RawPost:
    defaults = dict(
        source="linkedin",
        external_id="post-123",
        author_name="Alice Martin",
        author_url="https://linkedin.com/in/alice",
        content="Recherche développeur Python senior — mission 6 mois full remote",
        post_url="https://linkedin.com/posts/post-123",
        published_at=_now(),
        scraped_at=_now(),
    )
    return RawPost(**{**defaults, **kwargs})


def _user_profile(**kwargs) -> UserProfile:
    defaults = dict(
        email="stefano@example.com",
        full_name="Stefano Alletti",
        title="Senior Fullstack Developer",
        years_experience=15,
        preferred_contract_type=ContractType.FREELANCE,
        target_tjm=700.0,
        preferred_remote_mode=RemoteMode.FULL_REMOTE,
        skills=Stack.from_list(["Python", "FastAPI", "Docker"]),
        availability=_now(),
    )
    return UserProfile(**{**defaults, **kwargs})


class TestRawPost:
    def test_valid_raw_post(self):
        post = _raw_post()
        assert post.source == "linkedin"
        assert post.id is not None

    def test_unique_ids(self):
        assert _raw_post().id != _raw_post().id

    def test_refuses_empty_content(self):
        with pytest.raises(EmptyPostContentError):
            _raw_post(content="")

    def test_refuses_whitespace_content(self):
        with pytest.raises(EmptyPostContentError):
            _raw_post(content="   ")

    def test_refuses_newline_only_content(self):
        with pytest.raises(EmptyPostContentError):
            _raw_post(content="\n\t\n")


class TestUserProfile:
    def test_valid_user_profile(self):
        profile = _user_profile()
        assert profile.full_name == "Stefano Alletti"
        assert profile.email == "stefano@example.com"
        assert profile.id is not None
        assert profile.embedding is None

    def test_unique_ids(self):
        assert _user_profile().id != _user_profile().id


class TestUserProfileLocation:
    def test_location_defaults_to_none(self):
        profile = _user_profile()
        assert profile.location is None

    def test_location_can_be_set(self):
        assert _user_profile(location="Paris").location == "Paris"

    def test_location_can_be_none_explicitly(self):
        assert _user_profile(location=None).location is None

    def test_location_accepts_international_cities(self):
        for city in ("London", "Milan", "Berlin", "New York"):
            assert _user_profile(location=city).location == city

    def test_location_none_valid_with_full_remote(self):
        profile = _user_profile(location=None, preferred_remote_mode=RemoteMode.FULL_REMOTE)
        assert profile.location is None
        assert profile.preferred_remote_mode == RemoteMode.FULL_REMOTE

    def test_location_set_valid_with_hybrid(self):
        profile = _user_profile(location="Paris", preferred_remote_mode=RemoteMode.HYBRID)
        assert profile.location == "Paris"


class TestUserProfileEmail:
    def test_accepts_valid_email(self):
        profile = _user_profile(email="user@domain.com")
        assert profile.email == "user@domain.com"

    def test_accepts_subdomain_email(self):
        profile = _user_profile(email="user@mail.domain.co.uk")
        assert profile.email == "user@mail.domain.co.uk"

    def test_refuses_missing_at(self):
        with pytest.raises(InvalidEmailError):
            _user_profile(email="invalidemail.com")

    def test_refuses_missing_domain(self):
        with pytest.raises(InvalidEmailError):
            _user_profile(email="user@")

    def test_refuses_empty_email(self):
        with pytest.raises(InvalidEmailError):
            _user_profile(email="")

    def test_refuses_whitespace_email(self):
        with pytest.raises(InvalidEmailError):
            _user_profile(email="   ")

    def test_refuses_at_without_dot_in_domain(self):
        with pytest.raises(InvalidEmailError):
            _user_profile(email="user@nodomain")


def _analyzed_post(**kwargs) -> AnalyzedPost:
    defaults = dict(raw_post_id=_raw_post().id, summary="Mission Python senior full remote")
    return AnalyzedPost(**{**defaults, **kwargs})


class TestAnalyzedPost:
    def test_valid_analyzed_post(self):
        post = _analyzed_post()
        assert post.summary == "Mission Python senior full remote"
        assert post.id is not None
        assert post.created_at is not None

    def test_unique_ids(self):
        assert _analyzed_post().id != _analyzed_post().id

    def test_empty_summary_refused(self):
        with pytest.raises(EmptyAnalysisSummaryError):
            _analyzed_post(summary="")

    def test_whitespace_summary_refused(self):
        with pytest.raises(EmptyAnalysisSummaryError):
            _analyzed_post(summary="   ")

    def test_created_at_auto_generated(self):
        before = datetime.now(timezone.utc)
        post = _analyzed_post()
        assert post.created_at >= before

    def test_no_score_field(self):
        post = _analyzed_post()
        assert not hasattr(post, "match_score")
        assert not hasattr(post, "global_score")

    def test_detected_stack_defaults_to_empty_tuple(self):
        post = _analyzed_post()
        assert post.detected_stack == ()

    def test_detected_stack_preserved(self):
        post = _analyzed_post(detected_stack=("python", "fastapi"))
        assert post.detected_stack == ("python", "fastapi")

    def test_detected_contract_type_defaults_to_unknown(self):
        post = _analyzed_post()
        assert post.detected_contract_type == ContractType.UNKNOWN

    def test_detected_remote_mode_defaults_to_unknown(self):
        post = _analyzed_post()
        assert post.detected_remote_mode == RemoteMode.UNKNOWN

    def test_detected_tjm_defaults_to_none(self):
        post = _analyzed_post()
        assert post.detected_tjm is None

    def test_detected_tjm_preserved(self):
        post = _analyzed_post(detected_tjm=700.0)
        assert post.detected_tjm == pytest.approx(700.0)

    def test_optional_fields_default_to_none(self):
        post = _analyzed_post()
        assert post.title is None
        assert post.company is None
        assert post.location is None
        assert post.seniority is None

    def test_optional_fields_preserved(self):
        post = _analyzed_post(
            title="Lead Python Engineer",
            company="Acme Corp",
            location="Paris",
            seniority="senior",
        )
        assert post.title == "Lead Python Engineer"
        assert post.company == "Acme Corp"
        assert post.location == "Paris"
        assert post.seniority == "senior"

    def test_no_old_raw_fields(self):
        post = _analyzed_post()
        assert not hasattr(post, "required_skills")
        assert not hasattr(post, "nice_to_have_skills")
        assert not hasattr(post, "daily_rate")
        assert not hasattr(post, "contract_type")
        assert not hasattr(post, "remote_policy")
        assert not hasattr(post, "confidence_score")
        assert not hasattr(post, "is_mission")


