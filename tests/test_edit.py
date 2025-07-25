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

    # Force non-interactive mode to trigger the return code behavior
    monkeypatch.setattr("mcpm.commands.edit.is_non_interactive", lambda: True)

    runner = CliRunner()
    result = runner.invoke(edit, ["nonexistent"])  # Remove CLI parameters to match non-interactive mode

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

    # Force interactive mode
    monkeypatch.setattr("mcpm.commands.edit.is_non_interactive", lambda: False)
    monkeypatch.setattr("mcpm.commands.edit.should_force_operation", lambda: False)

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

    # Force interactive mode
    monkeypatch.setattr("mcpm.commands.edit.is_non_interactive", lambda: False)
    monkeypatch.setattr("mcpm.commands.edit.should_force_operation", lambda: False)

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
    assert "Interactive by default, or use CLI parameters for automation" in result.output
    assert "--new" in result.output
    assert "--editor" in result.output
    assert "--name" in result.output
    assert "--command" in result.output
    assert "--force" in result.output


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


def test_edit_stdio_server_non_interactive(monkeypatch):
    """Test editing a stdio server non-interactively."""
    test_server = STDIOServerConfig(
        name="test-server",
        command="python -m test_server",
        args=["--port", "8080"],
        env={"API_KEY": "old-secret"},
        profile_tags=["test-profile"],
    )

    mock_global_config = Mock()
    mock_global_config.get_server.return_value = test_server
    mock_global_config.remove_server.return_value = None
    mock_global_config.add_server.return_value = None
    monkeypatch.setattr("mcpm.commands.edit.global_config_manager", mock_global_config)

    # Force non-interactive mode
    monkeypatch.setattr("mcpm.commands.edit.is_non_interactive", lambda: True)

    runner = CliRunner()
    result = runner.invoke(edit, [
        "test-server",
        "--name", "updated-server",
        "--command", "python -m updated_server",
        "--args", "--port 9000 --debug",
        "--env", "API_KEY=new-secret,DEBUG=true"
    ])

    assert result.exit_code == 0
    assert "Successfully updated server" in result.output
    mock_global_config.remove_server.assert_called_once_with("test-server")
    mock_global_config.add_server.assert_called_once()


def test_edit_remote_server_non_interactive(monkeypatch):
    """Test editing a remote server non-interactively."""
    from mcpm.core.schema import RemoteServerConfig

    test_server = RemoteServerConfig(
        name="api-server",
        url="https://api.example.com",
        headers={"Authorization": "Bearer old-token"},
    )

    mock_global_config = Mock()
    mock_global_config.get_server.return_value = test_server
    mock_global_config.remove_server.return_value = None
    mock_global_config.add_server.return_value = None
    monkeypatch.setattr("mcpm.commands.edit.global_config_manager", mock_global_config)

    # Force non-interactive mode
    monkeypatch.setattr("mcpm.commands.edit.is_non_interactive", lambda: True)

    runner = CliRunner()
    result = runner.invoke(edit, [
        "api-server",
        "--name", "updated-api-server",
        "--url", "https://api-v2.example.com",
        "--headers", "Authorization=Bearer new-token,Content-Type=application/json"
    ])

    assert result.exit_code == 0
    assert "Successfully updated server" in result.output
    mock_global_config.remove_server.assert_called_once_with("api-server")
    mock_global_config.add_server.assert_called_once()


def test_edit_server_partial_update_non_interactive(monkeypatch):
    """Test editing only some fields of a server non-interactively."""
    test_server = STDIOServerConfig(
        name="test-server",
        command="python -m test_server",
        args=["--port", "8080"],
        env={"API_KEY": "secret"},
        profile_tags=["test-profile"],
    )

    mock_global_config = Mock()
    mock_global_config.get_server.return_value = test_server
    mock_global_config.remove_server.return_value = None
    mock_global_config.add_server.return_value = None
    monkeypatch.setattr("mcpm.commands.edit.global_config_manager", mock_global_config)

    # Force non-interactive mode
    monkeypatch.setattr("mcpm.commands.edit.is_non_interactive", lambda: True)

    runner = CliRunner()
    # Only update the command, leave other fields unchanged
    result = runner.invoke(edit, [
        "test-server",
        "--command", "python -m updated_server"
    ])

    assert result.exit_code == 0
    assert "Successfully updated server" in result.output
    mock_global_config.remove_server.assert_called_once_with("test-server")
    mock_global_config.add_server.assert_called_once()


def test_edit_server_invalid_env_format(monkeypatch):
    """Test error handling for invalid environment variable format."""
    test_server = STDIOServerConfig(
        name="test-server",
        command="python -m test_server",
        args=[],
        env={},
    )

    mock_global_config = Mock()
    mock_global_config.get_server.return_value = test_server
    monkeypatch.setattr("mcpm.commands.edit.global_config_manager", mock_global_config)

    # Force non-interactive mode
    monkeypatch.setattr("mcpm.commands.edit.is_non_interactive", lambda: True)

    runner = CliRunner()
    result = runner.invoke(edit, [
        "test-server",
        "--env", "invalid_format"  # Missing = sign
    ])

    assert result.exit_code == 1
    assert "Invalid environment variable format" in result.output or "Invalid key-value pair" in result.output


def test_edit_server_with_force_flag(monkeypatch):
    """Test editing a server with --force flag."""
    test_server = STDIOServerConfig(
        name="test-server",
        command="python -m test_server",
        args=[],
        env={},
    )

    mock_global_config = Mock()
    mock_global_config.get_server.return_value = test_server
    mock_global_config.remove_server.return_value = None
    mock_global_config.add_server.return_value = None
    monkeypatch.setattr("mcpm.commands.edit.global_config_manager", mock_global_config)

    runner = CliRunner()
    result = runner.invoke(edit, [
        "test-server",
        "--command", "python -m new_server",
        "--force"
    ])

    assert result.exit_code == 0
    assert "Successfully updated server" in result.output
    mock_global_config.remove_server.assert_called_once_with("test-server")
    mock_global_config.add_server.assert_called_once()


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
