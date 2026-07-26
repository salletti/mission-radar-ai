from dataclasses import dataclass


@dataclass(frozen=True)
class CollectPostsCommand:
    query: str
    limit: int
