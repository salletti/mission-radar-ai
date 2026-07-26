from abc import ABC, abstractmethod


class CVExtractorGateway(ABC):
    """Extracts raw text from a CV file. Implemented in Infrastructure/."""

    @abstractmethod
    async def extract_text(self, file_path: str) -> str: ...
