from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from src.Domain.Exception.domain_exceptions import EmptyPostContentError


@dataclass
class RawPost:
    """Raw LinkedIn post as scraped from Apify, before any analysis."""

    source: str
    external_id: str
    author_name: str
    author_url: str
    content: str
    post_url: str
    published_at: datetime
    scraped_at: datetime
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise EmptyPostContentError("RawPost content cannot be empty or whitespace-only")
