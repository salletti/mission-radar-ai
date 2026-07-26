class IdentityResolutionError(Exception):
    """Base class for MCP identity resolution errors."""


class MissingIdentityConfigurationError(IdentityResolutionError):
    """Raised when no profile identity is configured for this MCP transport."""


class InvalidIdentityConfigurationError(IdentityResolutionError):
    """Raised when the configured profile identity is not a valid UUID."""
