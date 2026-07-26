from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.Application.DTO.authenticated_identity import AuthenticatedIdentity


class TokenVerifierGateway(ABC):
    """Verifies a bearer token and resolves the caller's authenticated identity.
    Implemented in Infrastructure/."""

    @abstractmethod
    async def verify(self, token: str, expected_audience: str) -> AuthenticatedIdentity: ...
