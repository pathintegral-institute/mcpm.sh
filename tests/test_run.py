"""
Tests for MCPM v2.0 run command (global configuration model)

NOTE: These tests are written for the old subprocess.run implementation.
They need to be updated for the new FastMCP proxy architecture.
"""

import logging
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from mcpm.commands.run import run
from mcpm.core.schema import STDIOServerConfig
from mcpm.global_config import GlobalConfigManager


@pytest.mark.skip(reason="Needs updating for FastMCP proxy architecture")
def test_run_server_success(tmp_path):
    """Test successful server execution from global configuration"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    # Add a test server to global config
    test_server = STDIOServerConfig(
        name="test-server", command="echo", args=["hello", "world"], env={"TEST_VAR": "test-value"}
    )
    global_config_manager.add_server(test_server)

    # Mock the global config manager and subprocess
    with (
        patch("mcpm.commands.run.global_config_manager", global_config_manager),
        patch("mcpm.commands.run.subprocess.run") as mock_run,
        patch("mcpm.commands.usage.record_server_usage") as mock_usage,
    ):
        mock_run.return_value.returncode = 0

        runner = CliRunner()
        result = runner.invoke(run, ["test-server"])

        assert result.exit_code == 0

        # Verify subprocess.run was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args

        # Check command
        assert call_args[0][0] == ["echo", "hello", "world"]

        # Check environment
        env = call_args[1]["env"]
        assert env["TEST_VAR"] == "test-value"

        # Check usage was recorded
        mock_usage.assert_called_once_with("test-server", "run")


def test_run_server_not_found(tmp_path, caplog):
    """Test running non-existent server from global configuration"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    # Set logging level to capture INFO messages
    caplog.set_level(logging.INFO)

    # Mock the global config manager
    with patch("mcpm.commands.run.global_config_manager", global_config_manager):
        runner = CliRunner()
        result = runner.invoke(run, ["non-existent-server"])

        assert result.exit_code == 1

        assert len(caplog.records) == 5
        assert caplog.records[0].levelname == "ERROR"
        assert "Error: Server 'non-existent-server' not found" in caplog.records[0].message
        assert caplog.records[1].levelname == "WARNING"
        assert "Available options:" in caplog.records[1].message
        # Check that helpful info messages are included
        assert any("mcpm ls" in record.message for record in caplog.records)
        assert any("mcpm install" in record.message for record in caplog.records)


@pytest.mark.skip(reason="Needs updating for FastMCP proxy architecture")
def test_run_server_with_debug(tmp_path):
    """Test server execution with debug output"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    # Add a test server to global config
    test_server = STDIOServerConfig(name="debug-server", command="node", args=["server.js"], env={"DEBUG": "true"})
    global_config_manager.add_server(test_server)

    # Mock the global config manager and subprocess
    with (
        patch("mcpm.commands.run.global_config_manager", global_config_manager),
        patch("mcpm.commands.run.subprocess.run") as mock_run,
        patch("mcpm.commands.usage.record_server_usage"),
        patch.dict("os.environ", {"MCPM_DEBUG": "1"}),
    ):
        mock_run.return_value.returncode = 0

        runner = CliRunner()
        result = runner.invoke(run, ["debug-server"])

        assert result.exit_code == 0
        # Debug output goes to stderr, so we need to check stderr
        # In Click testing, both stdout and stderr go to output
        # We can't easily separate them in this test context


@pytest.mark.skip(reason="Needs updating for FastMCP proxy architecture")
def test_run_server_keyboard_interrupt(tmp_path, caplog):
    """Test server execution interrupted by keyboard"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    # Add a test server to global config
    test_server = STDIOServerConfig(name="interrupt-server", command="sleep", args=["10"])
    global_config_manager.add_server(test_server)

    # Mock the global config manager and subprocess
    with (
        patch("mcpm.commands.run.global_config_manager", global_config_manager),
        patch("mcpm.commands.run.subprocess.run") as mock_run,
        patch("mcpm.commands.usage.record_server_usage"),
    ):
        mock_run.side_effect = KeyboardInterrupt()

        runner = CliRunner()
        result = runner.invoke(run, ["interrupt-server"])

        assert result.exit_code == 130
        assert "Server execution interrupted" in caplog.text


@pytest.mark.skip(reason="Needs updating for FastMCP proxy architecture")
def test_run_server_command_not_found(tmp_path, caplog):
    """Test server execution with non-existent command"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    # Add a test server with non-existent command
    test_server = STDIOServerConfig(name="missing-cmd-server", command="nonexistent-command", args=["--arg"])
    global_config_manager.add_server(test_server)

    # Mock the global config manager and subprocess
    with (
        patch("mcpm.commands.run.global_config_manager", global_config_manager),
        patch("mcpm.commands.run.subprocess.run") as mock_run,
        patch("mcpm.commands.usage.record_server_usage"),
    ):
        mock_run.side_effect = FileNotFoundError()

        runner = CliRunner()
        result = runner.invoke(run, ["missing-cmd-server"])

        assert result.exit_code == 1
        assert "Command not found: nonexistent-command" in caplog.text
        assert "Make sure the required runtime is installed" in caplog.text


@pytest.mark.skip(reason="Needs updating for FastMCP proxy architecture")
def test_run_server_with_cwd(tmp_path):
    """Test server execution with custom working directory"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    # Create a test server with custom working directory
    # Note: cwd is not part of STDIOServerConfig schema, so we'll test without it
    # This test verifies the code handles missing cwd gracefully
    test_server = STDIOServerConfig(name="cwd-server", command="pwd", args=[])
    global_config_manager.add_server(test_server)

    # Mock the global config manager and subprocess
    with (
        patch("mcpm.commands.run.global_config_manager", global_config_manager),
        patch("mcpm.commands.run.subprocess.run") as mock_run,
        patch("mcpm.commands.usage.record_server_usage"),
    ):
        mock_run.return_value.returncode = 0

        runner = CliRunner()
        result = runner.invoke(run, ["cwd-server"])

        assert result.exit_code == 0

        # Verify subprocess.run was called with no cwd (None)
        call_args = mock_run.call_args
        assert call_args[1]["cwd"] is None


def test_run_empty_server_name(caplog):
    """Test running with empty server name"""
    runner = CliRunner()
    result = runner.invoke(run, [""])

    assert result.exit_code == 1
    assert "Error: Server name cannot be empty" in caplog.text


def test_run_whitespace_server_name(caplog):
    """Test running with whitespace-only server name"""
    runner = CliRunner()
    result = runner.invoke(run, ["   "])

    assert result.exit_code == 1
    assert "Error: Server name cannot be empty" in caplog.text


@pytest.mark.skip(reason="Needs updating for FastMCP proxy architecture")
def test_run_server_no_command(tmp_path, caplog):
    """Test server with missing command field"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    # Create an incomplete server config by directly manipulating the stored data
    # We'll add a server normally then break it
    test_server = STDIOServerConfig(name="broken-server", command="echo", args=["test"])
    global_config_manager.add_server(test_server)

    # Now manually break the server config by setting command to empty
    broken_server = STDIOServerConfig(
        name="broken-server",
        command="",  # Empty command
        args=["test"],
    )

    # Mock to return the broken server config
    with patch("mcpm.commands.run.global_config_manager") as mock_manager:
        mock_manager.get_server.return_value = broken_server

        runner = CliRunner()
        result = runner.invoke(run, ["broken-server"])

        assert result.exit_code == 1
        assert "Invalid command format for server 'broken-server'" in caplog.text
