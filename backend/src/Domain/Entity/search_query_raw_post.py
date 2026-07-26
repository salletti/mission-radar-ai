from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class SearchQueryRawPost:
    """Liaison entre une SearchQuery et un RawPost qu'elle a remontés.

    Permet de tracer quels posts ont été collectés par quelle query, sans dupliquer
    RawPost ni AnalyzedPost. Un même post peut être lié à N SearchQuery.
    """

    search_query_id: UUID
    raw_post_id: UUID
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
