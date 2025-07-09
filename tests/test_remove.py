"""
Tests for MCPM v2.0 remove command (global configuration model)
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from mcpm.commands.uninstall import uninstall
from mcpm.core.schema import STDIOServerConfig
from mcpm.global_config import GlobalConfigManager


def test_remove_server_success():
    """Test successful server removal from global configuration"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Setup temporary global config
        global_config_path = Path(tmp_dir) / "servers.json"
        global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

        # Add a test server to global config
        test_server = STDIOServerConfig(
            name="test-server",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-test"],
            env={"API_KEY": "test-key"},
        )
        global_config_manager.add_server(test_server)

        # Mock the global config manager in the remove command
        with patch("mcpm.commands.uninstall.global_config_manager", global_config_manager):
            runner = CliRunner()
            result = runner.invoke(uninstall, ["test-server", "--force"])

        assert result.exit_code == 0
        assert "Successfully removed server: test-server" in result.output
        assert not global_config_manager.server_exists("test-server")


def test_remove_server_not_found():
    """Test removal of non-existent server from global configuration"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Setup temporary global config
        global_config_path = Path(tmp_dir) / "servers.json"
        global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

        # Mock the global config manager
        with patch("mcpm.commands.uninstall.global_config_manager", global_config_manager):
            runner = CliRunner()
            result = runner.invoke(uninstall, ["non-existent-server", "--force"])

        assert result.exit_code == 0
        assert "Server 'non-existent-server' not found in global configuration" in result.output


def test_remove_server_cancelled():
    """Test removal cancellation"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Setup temporary global config
        global_config_path = Path(tmp_dir) / "servers.json"
        global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

        # Add a test server to global config
        test_server = STDIOServerConfig(
            name="test-server",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-test"],
            env={"API_KEY": "test-key"},
        )
        global_config_manager.add_server(test_server)

        # Mock the global config manager and user input
        with (
            patch("mcpm.commands.uninstall.global_config_manager", global_config_manager),
            patch("rich.prompt.Confirm.ask", return_value=False),
        ):
            runner = CliRunner()
            result = runner.invoke(uninstall, ["test-server"])

        assert result.exit_code == 0
        assert "Removal cancelled" in result.output
        # Server should still exist
        assert global_config_manager.server_exists("test-server")


def test_remove_server_with_confirmation():
    """Test removal with user confirmation"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Setup temporary global config
        global_config_path = Path(tmp_dir) / "servers.json"
        global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

        # Add a test server to global config
        test_server = STDIOServerConfig(
            name="test-server",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-test"],
            env={"API_KEY": "test-key"},
        )
        global_config_manager.add_server(test_server)

        # Mock the global config manager and user input
        with (
            patch("mcpm.commands.uninstall.global_config_manager", global_config_manager),
            patch("rich.prompt.Confirm.ask", return_value=True),
        ):
            runner = CliRunner()
            result = runner.invoke(uninstall, ["test-server"])

        assert result.exit_code == 0
        assert "Successfully removed server: test-server" in result.output
        assert not global_config_manager.server_exists("test-server")
