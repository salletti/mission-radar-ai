class LLMExtractionError(Exception):
    """Raised when the Groq API call fails (network, authentication, timeout)."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"LLM extraction failed: {reason}")
        self.reason = reason


class LLMResponseFormatError(Exception):
    """Raised when the LLM response is not valid JSON or does not match the CVProfile schema."""

    def __init__(self, reason: str) -> None:
        super().__init__(f"LLM response format error: {reason}")
        self.reason = reason


class AnalyzePostParsingError(LLMResponseFormatError):
    """Raised when the Groq response for analyze_post is not valid JSON."""
