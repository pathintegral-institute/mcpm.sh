"""
Test cases for share command with FastMCP proxy integration.
"""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from mcpm.commands.share import (
    find_available_port,
    find_installed_server,
    share,
)
from mcpm.core.schema import STDIOServerConfig
from mcpm.global_config import GlobalConfigManager


class TestShare:
    @pytest.mark.asyncio
    async def test_find_available_port_first_port_available(self):
        """Test find_available_port when the first port is available."""
        result = await find_available_port(9999)  # Use an uncommon port
        assert result == 9999

    @pytest.mark.asyncio
    async def test_find_available_port_finds_alternative(self):
        """Test find_available_port finds an alternative when preferred is busy."""
        import socket

        # Bind to the preferred port to make it busy
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", 9998))

            # Now try to find an available port starting from 9998
            result = await find_available_port(9998)
            assert result == 9999  # Should find the next available port
        finally:
            sock.close()

    def test_find_installed_server(self):
        """Test finding installed server in global configuration."""
        # Create a mock server config
        mock_config = STDIOServerConfig(name="test-server", command="python", args=["-m", "test_server"])

        with patch.object(GlobalConfigManager, "get_server", return_value=mock_config):
            server_config, location = find_installed_server("test-server")
            assert server_config == mock_config
            assert location == "global"

        with patch.object(GlobalConfigManager, "get_server", return_value=None):
            server_config, location = find_installed_server("nonexistent")
            assert server_config is None
            assert location is None

    def test_share_server_not_found(self):
        """Test share command with server not found."""
        runner = CliRunner()

        with patch.object(GlobalConfigManager, "get_server", return_value=None):
            result = runner.invoke(share, ["nonexistent-server"])
            assert result.exit_code != 0
            assert "not found" in result.output

    def test_share_empty_server_name(self):
        """Test share command with empty server name."""
        runner = CliRunner()
        result = runner.invoke(share, [""])
        assert result.exit_code != 0
        assert "cannot be empty" in result.output

    def test_share_help_shows_fastmcp_usage(self):
        """Test that share help shows FastMCP proxy usage."""
        runner = CliRunner()
        result = runner.invoke(share, ["--help"])
        assert result.exit_code == 0
        assert "FastMCP proxy" in result.output
