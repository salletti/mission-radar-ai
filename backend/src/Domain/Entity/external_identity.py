from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class ExternalIdentity:
    """Links an external identity provider's identity to a business UserProfile.
    Many-to-one with UserProfile: a user can have several linked identities
    (multiple providers, future service accounts), a single (provider, subject)
    always resolves to exactly one UserProfile."""

    user_profile_id: UUID
    provider: str
    subject: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
