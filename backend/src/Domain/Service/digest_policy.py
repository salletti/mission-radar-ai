from src.Domain.ValueObject.pipeline_enums import PipelineTrigger


class DigestPolicy:
    """Decides whether the digest step should be executed for a given pipeline trigger.

    USER trigger never sends an email — the dashboard refresh must stay silent.
    Extensible: add new guard methods below and compose them in should_send.
    """

    def should_send(self, trigger: PipelineTrigger) -> bool:
        return trigger in (PipelineTrigger.SCHEDULER, PipelineTrigger.SYSTEM)

    # Future guards (Phase 7.2+):
    # def _has_minimum_missions(self, count: int) -> bool: ...
    # def _not_already_sent_today(self, last_sent_at: datetime | None) -> bool: ...
    # def _user_has_email_enabled(self, user: UserProfile) -> bool: ...
