"""
Tests for the edit command
"""

import shlex
from unittest.mock import Mock

from click.testing import CliRunner

from mcpm.commands.edit import edit
from mcpm.core.schema import STDIOServerConfig


def test_edit_server_not_found(monkeypatch):
    """Test editing a server that doesn't exist."""
    mock_global_config = Mock()
    mock_global_config.get_server.return_value = None
    monkeypatch.setattr("mcpm.commands.edit.global_config_manager", mock_global_config)

    runner = CliRunner()
    result = runner.invoke(edit, ["nonexistent"])

    assert result.exit_code == 1
    assert "Server 'nonexistent' not found" in result.output


def test_edit_server_interactive_fallback(monkeypatch):
    """Test interactive mode fallback in non-terminal environment."""
    test_server = STDIOServerConfig(
        name="test-server",
        command="test-cmd",
        args=["arg1", "arg2"],
        env={"KEY": "value"},
        profile_tags=["test-profile"],
    )

    mock_global_config = Mock()
    mock_global_config.get_server.return_value = test_server
    monkeypatch.setattr("mcpm.commands.edit.global_config_manager", mock_global_config)

    runner = CliRunner()
    result = runner.invoke(edit, ["test-server"])

    # In test environment, interactive mode falls back and shows message
    assert result.exit_code == 0  # CliRunner may not properly handle our return codes
    assert "Current Configuration for 'test-server'" in result.output
    assert "test-cmd" in result.output
    assert "arg1 arg2" in result.output
    assert "KEY=value" in result.output
    assert "test-profile" in result.output
    assert "Interactive editing not available" in result.output
    assert "This command requires a terminal for interactive input" in result.output


def test_edit_server_with_spaces_in_args(monkeypatch):
    """Test display of arguments with spaces in the fallback view."""
    test_server = STDIOServerConfig(
        name="test-server",
        command="test-cmd",
        args=["arg with spaces", "another arg", "--flag=value with spaces"],
        env={"KEY": "value"},
        profile_tags=["test-profile"],
    )

    mock_global_config = Mock()
    mock_global_config.get_server.return_value = test_server
    monkeypatch.setattr("mcpm.commands.edit.global_config_manager", mock_global_config)

    runner = CliRunner()
    result = runner.invoke(edit, ["test-server"])

    # In test environment, interactive mode falls back and shows message
    assert result.exit_code == 0
    assert "Current Configuration for 'test-server'" in result.output
    assert "test-cmd" in result.output
    # Check that arguments with spaces are displayed correctly
    assert "arg with spaces another arg --flag=value with spaces" in result.output
    assert "Interactive editing not available" in result.output


def test_edit_command_help():
    """Test the edit command help output."""
    runner = CliRunner()
    result = runner.invoke(edit, ["--help"])

    assert result.exit_code == 0
    assert "Edit a server configuration" in result.output
    assert "Opens an interactive form editor" in result.output
    assert "mcpm edit time" in result.output
    assert "mcpm edit -N" in result.output
    assert "mcpm edit -e" in result.output
    assert "--new" in result.output
    assert "--editor" in result.output


def test_edit_editor_flag(monkeypatch):
    """Test the -e/--editor flag."""
    mock_global_config = Mock()
    mock_global_config.config_path = "/tmp/test_servers.json"
    monkeypatch.setattr("mcpm.commands.edit.global_config_manager", mock_global_config)

    # Mock os.path.exists to return True
    monkeypatch.setattr("os.path.exists", lambda path: True)

    # Mock subprocess.run to avoid actually opening an editor
    mock_subprocess = Mock()
    monkeypatch.setattr("subprocess.run", mock_subprocess)

    # Mock os.uname to simulate macOS
    mock_uname = Mock()
    mock_uname.sysname = "Darwin"
    monkeypatch.setattr("os.uname", lambda: mock_uname)

    runner = CliRunner()
    result = runner.invoke(edit, ["-e"])

    assert result.exit_code == 0
    assert "Opening global MCPM configuration in your default editor" in result.output
    assert "/tmp/test_servers.json" in result.output
    assert "After editing, restart any running MCP servers" in result.output

    # Verify subprocess.run was called with correct arguments
    mock_subprocess.assert_called_once_with(["open", "/tmp/test_servers.json"])


def test_shlex_argument_parsing():
    """Test that shlex correctly parses arguments with spaces."""
    # Test basic space-separated arguments
    result = shlex.split("arg1 arg2 arg3")
    assert result == ["arg1", "arg2", "arg3"]

    # Test quoted arguments with spaces
    result = shlex.split('arg1 "arg with spaces" arg3')
    assert result == ["arg1", "arg with spaces", "arg3"]

    # Test mixed quotes
    result = shlex.split("arg1 'arg with spaces' --flag=\"value with spaces\"")
    assert result == ["arg1", "arg with spaces", "--flag=value with spaces"]

    # Test empty string
    result = shlex.split("")
    assert result == []

    # Test single argument with spaces
    result = shlex.split('"single arg with spaces"')
    assert result == ["single arg with spaces"]
