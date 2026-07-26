"""Unit tests for DigestPolicy — no I/O, no DB, no external services."""
import pytest

from src.Domain.Service.digest_policy import DigestPolicy
from src.Domain.ValueObject.pipeline_enums import PipelineTrigger


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def _policy() -> DigestPolicy:
    return DigestPolicy()


# ---------------------------------------------------------------------------
# Tests — trigger USER
# ---------------------------------------------------------------------------


class TestDigestPolicyUserTrigger:
    def test_user_trigger_returns_false(self):
        assert _policy().should_send(PipelineTrigger.USER) is False

    def test_user_trigger_never_sends_email(self):
        result = _policy().should_send(PipelineTrigger.USER)
        assert not result


# ---------------------------------------------------------------------------
# Tests — trigger SCHEDULER
# ---------------------------------------------------------------------------


class TestDigestPolicySchedulerTrigger:
    def test_scheduler_trigger_returns_true(self):
        assert _policy().should_send(PipelineTrigger.SCHEDULER) is True

    def test_scheduler_trigger_sends_email(self):
        result = _policy().should_send(PipelineTrigger.SCHEDULER)
        assert result


# ---------------------------------------------------------------------------
# Tests — trigger SYSTEM
# ---------------------------------------------------------------------------


class TestDigestPolicySystemTrigger:
    def test_system_trigger_returns_true(self):
        assert _policy().should_send(PipelineTrigger.SYSTEM) is True


# ---------------------------------------------------------------------------
# Tests — separation: USER vs non-USER
# ---------------------------------------------------------------------------


class TestDigestPolicySeparation:
    def test_only_user_trigger_is_blocked(self):
        non_user_triggers = [PipelineTrigger.SCHEDULER, PipelineTrigger.SYSTEM]
        for trigger in non_user_triggers:
            assert _policy().should_send(trigger) is True, f"Expected True for {trigger}"

    def test_user_is_the_only_silent_trigger(self):
        assert _policy().should_send(PipelineTrigger.USER) is False
        assert _policy().should_send(PipelineTrigger.SCHEDULER) is True
