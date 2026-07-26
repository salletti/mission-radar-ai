"""Unit tests for DigestGenerator — no I/O, no DB, no external services."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.Domain.Entity.digest_email import DigestEmail
from src.Domain.Entity.user_profile import UserProfile
from src.Domain.Service.digest_generator import DigestGenerator
from src.Domain.ValueObject.contract_type import ContractType
from src.Domain.ValueObject.digest_mission import DigestMission
from src.Domain.ValueObject.remote_mode import RemoteMode
from src.Domain.ValueObject.stack import Stack


_AVAILABILITY = datetime(2026, 9, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_user(**kwargs) -> UserProfile:
    defaults = dict(
        email="jane@example.com",
        full_name="Jane Doe",
        title="Senior Python Engineer",
        years_experience=10,
        preferred_contract_type=ContractType.FREELANCE,
        target_tjm=700.0,
        preferred_remote_mode=RemoteMode.FULL_REMOTE,
        skills=Stack.from_list(["python", "fastapi"]),
        availability=_AVAILABILITY,
    )
    return UserProfile(**{**defaults, **kwargs})


def _make_digest_mission(score: float = 0.85) -> DigestMission:
    return DigestMission(
        mission_match_id=uuid4(),
        analyzed_post_id=uuid4(),
        final_score=score,
        summary="Mission Python.",
    )


def _generator() -> DigestGenerator:
    return DigestGenerator()


# ---------------------------------------------------------------------------
# Tests — returns DigestEmail
# ---------------------------------------------------------------------------


class TestDigestGeneratorReturnType:
    def test_returns_digest_email_instance(self):
        result = _generator().generate(_make_user(), [])
        assert isinstance(result, DigestEmail)

    def test_digest_email_has_auto_generated_id(self):
        result = _generator().generate(_make_user(), [])
        assert result.id is not None

    def test_digest_email_has_generated_at(self):
        result = _generator().generate(_make_user(), [])
        assert result.generated_at is not None


# ---------------------------------------------------------------------------
# Tests — user fields propagated
# ---------------------------------------------------------------------------


class TestDigestGeneratorUserFields:
    def test_propagates_user_id(self):
        user = _make_user()
        result = _generator().generate(user, [])
        assert result.user_id == user.id

    def test_propagates_user_email(self):
        result = _generator().generate(_make_user(email="jane@example.com"), [])
        assert result.user_email == "jane@example.com"

    def test_propagates_user_name(self):
        result = _generator().generate(_make_user(full_name="Jane Doe"), [])
        assert result.user_name == "Jane Doe"


# ---------------------------------------------------------------------------
# Tests — missions propagated
# ---------------------------------------------------------------------------


class TestDigestGeneratorMissions:
    def test_empty_missions_list_produces_zero_count(self):
        result = _generator().generate(_make_user(), [])
        assert result.mission_count == 0

    def test_missions_stored_as_tuple(self):
        missions = [_make_digest_mission(), _make_digest_mission(score=0.7)]
        result = _generator().generate(_make_user(), missions)
        assert isinstance(result.missions, tuple)
        assert len(result.missions) == 2

    def test_missions_order_preserved(self):
        m1 = _make_digest_mission(score=0.9)
        m2 = _make_digest_mission(score=0.7)
        result = _generator().generate(_make_user(), [m1, m2])
        assert result.missions[0] is m1
        assert result.missions[1] is m2


# ---------------------------------------------------------------------------
# Tests — subject generation
# ---------------------------------------------------------------------------


class TestDigestGeneratorSubject:
    def test_subject_zero_missions(self):
        result = _generator().generate(_make_user(), [])
        assert result.subject == "Mission Radar AI — Aucune nouvelle mission aujourd'hui"

    def test_subject_one_mission_singular(self):
        result = _generator().generate(_make_user(), [_make_digest_mission()])
        assert result.subject == "Mission Radar AI — 1 nouvelle mission aujourd'hui"

    def test_subject_two_missions_plural(self):
        missions = [_make_digest_mission(), _make_digest_mission()]
        result = _generator().generate(_make_user(), missions)
        assert result.subject == "Mission Radar AI — 2 nouvelles missions aujourd'hui"

    def test_subject_eight_missions_plural(self):
        missions = [_make_digest_mission() for _ in range(8)]
        result = _generator().generate(_make_user(), missions)
        assert result.subject == "Mission Radar AI — 8 nouvelles missions aujourd'hui"

    def test_subject_contains_mission_radar_brand(self):
        result = _generator().generate(_make_user(), [])
        assert "Mission Radar AI" in result.subject
