class ApplicationError(Exception):
    """Base class for application-layer errors."""


class UserProfileNotFoundError(ApplicationError):
    """Raised when a required UserProfile cannot be found."""


class ProfileEmbeddingMissingError(ApplicationError):
    """Raised when a UserProfile has no embedding and matching cannot be computed."""


class PipelineAlreadyRunningError(ApplicationError):
    """Raised when a pipeline is already running for the given user."""


class UserProfileNotLinkedError(ApplicationError):
    """Raised when an authenticated identity has no UserProfile linked to it yet
    (the caller is authenticated, the provider knows them — no ExternalIdentity
    link exists). Signals "complete onboarding", not "unauthenticated"."""
