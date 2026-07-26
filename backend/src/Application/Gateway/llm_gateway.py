from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.Application.DTO.cv_profile import CVProfile
    from src.Domain.Entity.raw_post import RawPost
    from src.Domain.Entity.user_profile import UserProfile
    from src.Domain.ValueObject.post_analysis import PostAnalysis


class LLMGateway(ABC):
    """Structured extraction and text generation via LLM. Implemented in Infrastructure/."""

    @abstractmethod
    async def extract_profile_from_cv(self, cv_text: str) -> CVProfile: ...

    @abstractmethod
    async def summarize_mission(self, content: str) -> str: ...

    @abstractmethod
    async def generate_search_queries(self, profile: UserProfile) -> list[dict]: ...

    @abstractmethod
    async def analyze_post(self, raw_post: RawPost) -> PostAnalysis: ...
