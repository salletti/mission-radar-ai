class TokenVerificationError(Exception):
    """Raised when a bearer token fails signature, issuer, audience, or expiry validation."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"Token verification failed: {reason}")
        self.reason = reason
