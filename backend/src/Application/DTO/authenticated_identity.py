from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class AuthenticatedIdentity:
    """The result of authenticating a caller, independent of the mechanism
    (JWT/Auth0 today, any OIDC-compatible provider tomorrow). Output of
    TokenVerifierGateway, input to ResolveIdentity.

    provider/subject/email are first-class fields because current business
    use cases already depend on them (identity resolution, onboarding,
    UserProfile.email, digest emails). Everything else a provider might carry
    (scopes, roles, organization...) stays in `claims` until a real use case
    needs it promoted the same way.
    """

    provider: str
    subject: str
    email: Optional[str] = None
    claims: Mapping[str, Any] = field(default_factory=dict)
