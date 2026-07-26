class CVExtractionError(Exception):
    """Wraps pdfminer errors so they never leak to Application or Domain."""

    def __init__(self, file_path: str, reason: str) -> None:
        super().__init__(f"CV extraction failed for '{file_path}': {reason}")
        self.file_path = file_path
        self.reason = reason
