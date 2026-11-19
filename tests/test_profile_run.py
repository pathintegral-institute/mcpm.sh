"""
Tests for `mcpm profile run` passing profile metadata to the proxy.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcpm.commands.profile.run import run_profile_fastmcp
from mcpm.core.schema import ProfileMetadata, RemoteServerConfig


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "metadata, expected_instructions",
    [
        (
            ProfileMetadata(name="web", description="Prefer search tools for web lookups."),
            "Prefer search tools for web lookups.",
        ),
        (ProfileMetadata(name="web"), None),
        (ProfileMetadata(name="web", description=""), None),
        (None, None),
    ],
)
async def test_profile_run_uses_description_as_instructions(metadata, expected_instructions):
    """The profile description becomes the proxy's server instructions."""
    servers = [RemoteServerConfig(name="test", url="http://example.com")]
    proxy = Mock()
    proxy.run_stdio_async = AsyncMock()

    with (
        patch("mcpm.commands.profile.run.create_mcpm_proxy", AsyncMock(return_value=proxy)) as mock_create,
        patch("mcpm.commands.profile.run.profile_config_manager") as mock_manager,
    ):
        mock_manager.get_profile_metadata.return_value = metadata

        result = await run_profile_fastmcp(servers, "web")

    assert result == 0
    mock_manager.get_profile_metadata.assert_called_once_with("web")
    assert mock_create.call_args.kwargs["instructions"] == expected_instructions
