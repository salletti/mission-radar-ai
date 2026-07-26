from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class SaveProfileResult:
    profile_id: UUID
    email: str
    status: str  # "created" | "updated"
    search_queries: list[str] = field(default_factory=list)

    @property
    def search_queries_count(self) -> int:
        return len(self.search_queries)
