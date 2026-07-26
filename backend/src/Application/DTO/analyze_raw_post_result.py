from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from src.Domain.Entity.analyzed_post import AnalyzedPost


@dataclass
class AnalyzeRawPostResult:
    status: str  # "analyzed" | "skipped" | "already_analyzed"
    analyzed_post_id: UUID | None = None
    analyzed_post: AnalyzedPost | None = None
    reason: str | None = None
