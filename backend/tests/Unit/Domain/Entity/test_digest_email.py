"""Unit tests for DigestEmail — no I/O, no DB, no external services."""
from uuid import uuid4

from src.Domain.Entity.digest_email import DigestEmail
from src.Domain.ValueObject.digest_mission import DigestMission
from src.Domain.ValueObject.remote_mode import RemoteMode


_USER_ID = uuid4()
_USER_EMAIL = "user@example.com"
_USER_NAME = "Jane Doe"


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def _make_digest_mission(score: float = 0.85) -> DigestMission:
    return DigestMission(
        mission_match_id=uuid4(),
        analyzed_post_id=uuid4(),
        final_score=score,
        summary="Mission Python.",
    )


def _make_digest_email(missions: tuple[DigestMission, ...] = ()) -> DigestEmail:
    return DigestEmail(
        user_id=_USER_ID,
        user_email=_USER_EMAIL,
        user_name=_USER_NAME,
        subject="Mission Radar AI — 3 nouvelles missions aujourd'hui",
        missions=missions,
    )


# ---------------------------------------------------------------------------
# Tests — identity & auto-fields
# ---------------------------------------------------------------------------


class TestDigestEmailIdentity:
    def test_id_is_auto_generated(self):
        email = _make_digest_email()
        assert email.id is not None

    def test_two_emails_have_different_ids(self):
        a = _make_digest_email()
        b = _make_digest_email()
        assert a.id != b.id

    def test_generated_at_is_auto_set(self):
        email = _make_digest_email()
        assert email.generated_at is not None


# ---------------------------------------------------------------------------
# Tests — stored fields
# ---------------------------------------------------------------------------


class TestDigestEmailFields:
    def test_stores_user_id(self):
        email = _make_digest_email()
        assert email.user_id == _USER_ID

    def test_stores_user_email(self):
        email = _make_digest_email()
        assert email.user_email == _USER_EMAIL

    def test_stores_user_name(self):
        email = _make_digest_email()
        assert email.user_name == _USER_NAME

    def test_stores_subject(self):
        email = _make_digest_email()
        assert email.subject == "Mission Radar AI — 3 nouvelles missions aujourd'hui"

    def test_stores_missions_as_tuple(self):
        mission = _make_digest_mission()
        email = _make_digest_email(missions=(mission,))
        assert isinstance(email.missions, tuple)
        assert email.missions[0] is mission


# ---------------------------------------------------------------------------
# Tests — mission_count property
# ---------------------------------------------------------------------------


class TestDigestEmailMissionCount:
    def test_mission_count_zero(self):
        email = _make_digest_email(missions=())
        assert email.mission_count == 0

    def test_mission_count_one(self):
        email = _make_digest_email(missions=(_make_digest_mission(),))
        assert email.mission_count == 1

    def test_mission_count_multiple(self):
        missions = tuple(_make_digest_mission(score=0.9 - i * 0.1) for i in range(5))
        email = _make_digest_email(missions=missions)
        assert email.mission_count == 5
