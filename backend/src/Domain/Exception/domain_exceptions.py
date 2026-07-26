class DomainException(Exception):
    """Base class for all domain exceptions."""


class InvalidTJMError(DomainException):
    """Raised when a TJM value is invalid (e.g. negative amount)."""


class InvalidScoreError(DomainException):
    """Raised when a score value is outside the [0.0, 1.0] range."""


class InvalidContractTypeError(DomainException):
    """Raised when a contract type value is not in the allowed set."""


class InvalidRemoteModeError(DomainException):
    """Raised when a remote mode value is not in the allowed set."""


class EmptyPostContentError(DomainException):
    """Raised when a post content is empty or whitespace-only."""


class InvalidEmailError(DomainException):
    """Raised when an email address has an invalid format."""


class MissionMatchNotFoundError(DomainException):
    """Raised when a MissionMatch cannot be found."""


class InvalidSearchQueryError(DomainException):
    """Raised when a SearchQuery has invalid fields (empty query, non-positive limit…)."""


class EmptyAnalysisSummaryError(DomainException):
    """Raised when PostAnalysis summary is empty or whitespace-only."""


class InvalidPipelineTransitionError(DomainException):
    """Raised when a PipelineRun state machine transition is invalid."""
