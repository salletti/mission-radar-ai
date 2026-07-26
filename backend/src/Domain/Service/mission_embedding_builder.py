from __future__ import annotations

from src.Domain.Entity.analyzed_post import AnalyzedPost


class MissionEmbeddingBuilder:
    """Pure domain service — builds a matching-optimized text from an AnalyzedPost.

    Output fed to EmbeddingGateway.embed_text() in the Application layer.
    No I/O, no Application/Infrastructure imports.
    """

    def build_matching_text(self, post: AnalyzedPost) -> str:
        parts: list[str] = []
        if post.title:
            parts.append(post.title)
        if post.company:
            parts.append(post.company)
        parts.append(post.summary)
        if post.detected_stack:
            parts.append(" ".join(post.detected_stack))
        parts.append(post.detected_contract_type.value)
        parts.append(post.detected_remote_mode.value)
        if post.location:
            parts.append(post.location)
        return "\n".join(parts)
