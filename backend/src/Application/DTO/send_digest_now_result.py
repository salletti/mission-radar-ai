from dataclasses import dataclass


@dataclass(frozen=True)
class SendDigestNowResult:
    status: str  # "sent" | "failed"
    missions_count: int
    provider_message_id: str | None
    error_message: str | None
