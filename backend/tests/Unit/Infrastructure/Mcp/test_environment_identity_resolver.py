"""Unit tests for EnvironmentIdentityResolver — pure config read, no I/O."""
from uuid import UUID

import pytest

from src.Infrastructure.Mcp.Identity.environment_identity_resolver import EnvironmentIdentityResolver
from src.Infrastructure.Mcp.Identity.exceptions import (
    InvalidIdentityConfigurationError,
    MissingIdentityConfigurationError,
)

_PROFILE_ID = "89043b47-7e5a-4044-9555-475e77da6eca"


@pytest.mark.asyncio
async def test_configured_uuid_is_returned() -> None:
    resolver = EnvironmentIdentityResolver(profile_id=f"  {_PROFILE_ID}  ")

    identity = await resolver.resolve()

    assert identity == UUID(_PROFILE_ID)


@pytest.mark.asyncio
async def test_empty_config_raises_missing_identity_configuration_error() -> None:
    resolver = EnvironmentIdentityResolver(profile_id="")

    with pytest.raises(MissingIdentityConfigurationError):
        await resolver.resolve()


@pytest.mark.asyncio
async def test_whitespace_only_config_raises_missing_identity_configuration_error() -> None:
    resolver = EnvironmentIdentityResolver(profile_id="   ")

    with pytest.raises(MissingIdentityConfigurationError):
        await resolver.resolve()


@pytest.mark.asyncio
async def test_malformed_uuid_raises_invalid_identity_configuration_error() -> None:
    resolver = EnvironmentIdentityResolver(profile_id="not-a-uuid")

    with pytest.raises(InvalidIdentityConfigurationError):
        await resolver.resolve()
