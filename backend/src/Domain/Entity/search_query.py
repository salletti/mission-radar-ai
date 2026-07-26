from dataclasses import dataclass, field
from uuid import UUID, uuid4

from src.Domain.Exception.domain_exceptions import InvalidSearchQueryError


@dataclass
class SearchQuery:
    """A search query derived from a user profile, targeting one scraping source.

    Persisted so the scheduler can read them dynamically (Phase 3.5).
    Regenerated from scratch (DELETE + INSERT) each time the profile is saved.
    """

    user_profile_id: UUID
    query: str      # e.g. "python freelance paris"
    source: str     # "linkedin" — extensible to indeed, free-work, etc.
    limit: int      # max posts to scrape per query run
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise InvalidSearchQueryError("query cannot be empty")
        if self.limit <= 0:
            raise InvalidSearchQueryError("limit must be positive")
        if not self.source.strip():
            raise InvalidSearchQueryError("source cannot be empty")
