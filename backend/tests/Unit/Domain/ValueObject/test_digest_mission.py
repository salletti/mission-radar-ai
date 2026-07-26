"""Unit tests for DigestMission — no I/O, no DB, no external services."""
from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from src.Domain.ValueObject.digest_mission import DigestMission
from src.Domain.ValueObject.remote_mode import RemoteMode


_MISSION_MATCH_ID = uuid4()
_ANALYZED_POST_ID = uuid4()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _make_digest_mission(**kwargs) -> DigestMission:
    defaults = dict(
        mission_match_id=_MISSION_MATCH_ID,
        analyzed_post_id=_ANALYZED_POST_ID,
        final_score=0.85,
        summary="Mission Python FastAPI full remote.",
    )
    return DigestMission(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# Tests — required fields
# ---------------------------------------------------------------------------


class TestDigestMissionRequiredFields:
    def test_stores_mission_match_id(self):
        m = _make_digest_mission()
        assert m.mission_match_id == _MISSION_MATCH_ID

    def test_stores_analyzed_post_id(self):
        m = _make_digest_mission()
        assert m.analyzed_post_id == _ANALYZED_POST_ID

    def test_stores_final_score(self):
        m = _make_digest_mission(final_score=0.92)
        assert m.final_score == pytest.approx(0.92)

    def test_stores_summary(self):
        m = _make_digest_mission(summary="Mission Django.")
        assert m.summary == "Mission Django."


# ---------------------------------------------------------------------------
# Tests — optional fields / defaults
# ---------------------------------------------------------------------------


class TestDigestMissionOptionalFields:
    def test_title_defaults_to_none(self):
        assert _make_digest_mission().title is None

    def test_company_defaults_to_none(self):
        assert _make_digest_mission().company is None

    def test_detected_stack_defaults_to_empty_tuple(self):
        assert _make_digest_mission().detected_stack == ()

    def test_detected_remote_mode_defaults_to_unknown(self):
        assert _make_digest_mission().detected_remote_mode == RemoteMode.UNKNOWN

    def test_detected_tjm_defaults_to_none(self):
        assert _make_digest_mission().detected_tjm is None

    def test_post_url_defaults_to_none(self):
        assert _make_digest_mission().post_url is None

    def test_stores_optional_fields_when_provided(self):
        m = _make_digest_mission(
            title="Lead Python Engineer",
            company="Acme Corp",
            detected_stack=("python", "fastapi"),
            detected_remote_mode=RemoteMode.FULL_REMOTE,
            detected_tjm=700.0,
            post_url="https://linkedin.com/posts/abc123",
        )
        assert m.title == "Lead Python Engineer"
        assert m.company == "Acme Corp"
        assert m.detected_stack == ("python", "fastapi")
        assert m.detected_remote_mode == RemoteMode.FULL_REMOTE
        assert m.detected_tjm == pytest.approx(700.0)
        assert m.post_url == "https://linkedin.com/posts/abc123"


# ---------------------------------------------------------------------------
# Tests — immutability (frozen dataclass)
# ---------------------------------------------------------------------------


class TestDigestMissionImmutability:
    def test_is_frozen(self):
        m = _make_digest_mission()
        with pytest.raises((FrozenInstanceError, AttributeError)):
            m.final_score = 0.0  # type: ignore[misc]

    def test_two_identical_missions_are_equal(self):
        m1 = _make_digest_mission()
        m2 = _make_digest_mission()
        assert m1 == m2

    def test_different_scores_are_not_equal(self):
        m1 = _make_digest_mission(final_score=0.8)
        m2 = _make_digest_mission(final_score=0.9)
        assert m1 != m2
