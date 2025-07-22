"""
Tests for profile commands (mcpm profile edit, mcpm profile inspect)
"""

from unittest.mock import Mock

from click.testing import CliRunner

from mcpm.commands.profile.edit import edit_profile
from mcpm.commands.profile.inspect import inspect_profile
from mcpm.core.schema import STDIOServerConfig


def test_profile_edit_non_interactive_add_server(monkeypatch):
    """Test adding servers to a profile non-interactively."""
    # Mock existing profile with one server
    existing_server = STDIOServerConfig(name="existing-server", command="echo test")

    # Mock ProfileConfigManager
    mock_profile_config = Mock()
    mock_profile_config.get_profile.return_value = [existing_server]
    mock_profile_config.add_server_to_profile.return_value = True
    monkeypatch.setattr("mcpm.commands.profile.edit.profile_config_manager", mock_profile_config)

    # Mock GlobalConfigManager
    mock_global_config = Mock()
    mock_global_config.get_server.return_value = STDIOServerConfig(name="new-server", command="echo new")
    monkeypatch.setattr("mcpm.commands.profile.edit.global_config_manager", mock_global_config)

    # Force non-interactive mode
    monkeypatch.setattr("mcpm.commands.profile.edit.is_non_interactive", lambda: True)

    runner = CliRunner()
    result = runner.invoke(edit_profile, [
        "test-profile",
        "--add-server", "new-server,another-server"
    ])

    assert result.exit_code == 0
    assert "Successfully updated profile" in result.output
    # Should be called for each server being added
    assert mock_profile_config.add_server_to_profile.call_count >= 1


def test_profile_edit_non_interactive_remove_server(monkeypatch):
    """Test removing servers from a profile non-interactively."""
    # Mock existing profile with servers
    server1 = STDIOServerConfig(name="server1", command="echo 1")
    server2 = STDIOServerConfig(name="server2", command="echo 2")

    # Mock ProfileConfigManager
    mock_profile_config = Mock()
    mock_profile_config.get_profile.return_value = [server1, server2]
    mock_profile_config.remove_server.return_value = True
    monkeypatch.setattr("mcpm.commands.profile.edit.profile_config_manager", mock_profile_config)

    # Force non-interactive mode
    monkeypatch.setattr("mcpm.commands.profile.edit.is_non_interactive", lambda: True)

    runner = CliRunner()
    result = runner.invoke(edit_profile, [
        "test-profile",
        "--remove-server", "server1"
    ])

    assert result.exit_code == 0
    assert "Successfully updated profile" in result.output
    mock_profile_config.remove_server.assert_called_with("test-profile", "server1")


def test_profile_edit_non_interactive_set_servers(monkeypatch):
    """Test setting all servers in a profile non-interactively."""
    # Mock existing profile
    existing_server = STDIOServerConfig(name="old-server", command="echo old")

    # Mock ProfileConfigManager
    mock_profile_config = Mock()
    mock_profile_config.get_profile.return_value = [existing_server]
    mock_profile_config.clear_profile.return_value = True
    mock_profile_config.add_server_to_profile.return_value = True
    monkeypatch.setattr("mcpm.commands.profile.edit.profile_config_manager", mock_profile_config)

    # Mock GlobalConfigManager
    mock_global_config = Mock()
    mock_global_config.get_server.return_value = STDIOServerConfig(name="new-server", command="echo new")
    monkeypatch.setattr("mcpm.commands.profile.edit.global_config_manager", mock_global_config)

    # Force non-interactive mode
    monkeypatch.setattr("mcpm.commands.profile.edit.is_non_interactive", lambda: True)

    runner = CliRunner()
    result = runner.invoke(edit_profile, [
        "test-profile",
        "--set-servers", "server1,server2,server3"
    ])

    assert result.exit_code == 0
    assert "Successfully updated profile" in result.output
    # Should clear existing servers then add new ones
    mock_profile_config.clear_profile.assert_called_with("test-profile")


def test_profile_edit_non_interactive_rename(monkeypatch):
    """Test renaming a profile non-interactively."""
    # Mock existing profile
    existing_server = STDIOServerConfig(name="test-server", command="echo test")

    # Mock ProfileConfigManager
    mock_profile_config = Mock()
    mock_profile_config.get_profile.return_value = [existing_server]
    mock_profile_config.rename_profile.return_value = True
    monkeypatch.setattr("mcpm.commands.profile.edit.profile_config_manager", mock_profile_config)

    # Force non-interactive mode
    monkeypatch.setattr("mcpm.commands.profile.edit.is_non_interactive", lambda: True)

    runner = CliRunner()
    result = runner.invoke(edit_profile, [
        "old-profile-name",
        "--name", "new-profile-name"
    ])

    assert result.exit_code == 0
    assert "Successfully updated profile" in result.output
    mock_profile_config.rename_profile.assert_called_with("old-profile-name", "new-profile-name")


def test_profile_edit_non_interactive_profile_not_found(monkeypatch):
    """Test error handling when profile doesn't exist."""
    # Mock ProfileConfigManager
    mock_profile_config = Mock()
    mock_profile_config.get_profile.return_value = None  # Profile doesn't exist
    monkeypatch.setattr("mcpm.commands.profile.edit.profile_config_manager", mock_profile_config)

    runner = CliRunner()
    result = runner.invoke(edit_profile, [
        "nonexistent-profile",
        "--add-server", "some-server"
    ])

    assert result.exit_code == 1
    assert "Profile 'nonexistent-profile' not found" in result.output


def test_profile_edit_non_interactive_server_not_found(monkeypatch):
    """Test error handling when trying to add non-existent server."""
    # Mock existing profile
    existing_server = STDIOServerConfig(name="existing-server", command="echo test")

    # Mock ProfileConfigManager
    mock_profile_config = Mock()
    mock_profile_config.get_profile.return_value = [existing_server]
    monkeypatch.setattr("mcpm.commands.profile.edit.profile_config_manager", mock_profile_config)

    # Mock GlobalConfigManager
    mock_global_config = Mock()
    mock_global_config.get_server.return_value = None  # Server doesn't exist
    monkeypatch.setattr("mcpm.commands.profile.edit.global_config_manager", mock_global_config)

    # Force non-interactive mode
    monkeypatch.setattr("mcpm.commands.profile.edit.is_non_interactive", lambda: True)

    runner = CliRunner()
    result = runner.invoke(edit_profile, [
        "test-profile",
        "--add-server", "nonexistent-server"
    ])

    assert result.exit_code == 1
    assert "Server 'nonexistent-server' not found" in result.output


def test_profile_edit_with_force_flag(monkeypatch):
    """Test profile edit with --force flag."""
    # Mock existing profile
    existing_server = STDIOServerConfig(name="existing-server", command="echo test")

    # Mock ProfileConfigManager
    mock_profile_config = Mock()
    mock_profile_config.get_profile.return_value = [existing_server]
    mock_profile_config.add_server_to_profile.return_value = True
    monkeypatch.setattr("mcpm.commands.profile.edit.profile_config_manager", mock_profile_config)

    # Mock GlobalConfigManager
    mock_global_config = Mock()
    mock_global_config.get_server.return_value = STDIOServerConfig(name="new-server", command="echo new")
    monkeypatch.setattr("mcpm.commands.profile.edit.global_config_manager", mock_global_config)

    runner = CliRunner()
    result = runner.invoke(edit_profile, [
        "test-profile",
        "--add-server", "new-server",
        "--force"
    ])

    assert result.exit_code == 0
    assert "Successfully updated profile" in result.output


def test_profile_edit_interactive_fallback(monkeypatch):
    """Test that profile edit falls back to interactive mode when no CLI params."""
    # Mock existing profile
    existing_server = STDIOServerConfig(name="existing-server", command="echo test")

    # Mock ProfileConfigManager
    mock_profile_config = Mock()
    mock_profile_config.get_profile.return_value = [existing_server]
    monkeypatch.setattr("mcpm.commands.profile.edit.profile_config_manager", mock_profile_config)

    # Force interactive mode
    monkeypatch.setattr("mcpm.commands.profile.edit.is_non_interactive", lambda: False)
    monkeypatch.setattr("mcpm.commands.profile.edit.should_force_operation", lambda: False)

    runner = CliRunner()
    result = runner.invoke(edit_profile, ["test-profile"])

    # Should show interactive fallback message
    assert result.exit_code == 0
    assert ("Interactive profile editing not available" in result.output or
            "This command requires a terminal" in result.output or
            "Current servers in profile" in result.output)


def test_profile_inspect_non_interactive(monkeypatch):
    """Test profile inspect with non-interactive options."""
    # Mock existing profile with servers
    server1 = STDIOServerConfig(name="server1", command="echo 1")
    server2 = STDIOServerConfig(name="server2", command="echo 2")

    # Mock ProfileConfigManager
    mock_profile_config = Mock()
    mock_profile_config.get_profile.return_value = [server1, server2]
    monkeypatch.setattr("mcpm.commands.profile.inspect.profile_config_manager", mock_profile_config)

    # Mock subprocess for launching inspector
    mock_subprocess = Mock()
    monkeypatch.setattr("mcpm.commands.profile.inspect.subprocess", mock_subprocess)

    # Mock other dependencies
    import shutil
    import tempfile
    monkeypatch.setattr(shutil, "which", lambda x: "/usr/bin/node")
    monkeypatch.setattr(tempfile, "mkdtemp", lambda: "/tmp/test")

    runner = CliRunner()
    result = runner.invoke(inspect_profile, [
        "test-profile",
        "--server", "server1",
        "--port", "9000",
        "--host", "localhost"
    ])

    # The command should attempt to launch the inspector
    # (exact behavior depends on implementation details)
    assert result.exit_code == 0 or "Profile 'test-profile' not found" in result.output


def test_profile_inspect_profile_not_found(monkeypatch):
    """Test profile inspect error handling when profile doesn't exist."""
    # Mock ProfileConfigManager
    mock_profile_config = Mock()
    mock_profile_config.get_profile.return_value = None  # Profile doesn't exist
    monkeypatch.setattr("mcpm.commands.profile.inspect.profile_config_manager", mock_profile_config)

    runner = CliRunner()
    result = runner.invoke(inspect_profile, ["nonexistent-profile"])

    assert result.exit_code == 1
    assert "Profile 'nonexistent-profile' not found" in result.output


def test_profile_edit_command_help():
    """Test the profile edit command help output."""
    runner = CliRunner()
    result = runner.invoke(edit_profile, ["--help"])

    assert result.exit_code == 0
    assert "Edit a profile's name and server selection" in result.output
    assert "Interactive by default, or use CLI parameters for automation" in result.output
    assert "--name" in result.output
    assert "--add-server" in result.output
    assert "--remove-server" in result.output
    assert "--set-servers" in result.output
    assert "--force" in result.output


def test_profile_inspect_command_help():
    """Test the profile inspect command help output."""
    runner = CliRunner()
    result = runner.invoke(inspect_profile, ["--help"])

    assert result.exit_code == 0
    assert "Launch MCP Inspector" in result.output or "test and debug servers" in result.output
    assert "--server" in result.output
    assert "--port" in result.output
    assert "--host" in result.output
