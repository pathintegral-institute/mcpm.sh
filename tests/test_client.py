"""
Tests for the client commands (ls, set, edit)
"""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from mcpm.clients.client_registry import ClientRegistry
from mcpm.commands.client import client, edit_client


def test_client_ls_command(monkeypatch, tmp_path):
    """Test the 'client ls' command - should list all supported MCP clients and their enabled MCPM servers"""
    # Mock supported clients
    supported_clients = ["claude-desktop", "windsurf", "cursor"]
    monkeypatch.setattr(
        "mcpm.commands.client.ClientRegistry.get_supported_clients", Mock(return_value=supported_clients)
    )

    # Mock installed clients
    installed_clients = {"claude-desktop": True, "windsurf": False, "cursor": True}
    monkeypatch.setattr(
        "mcpm.commands.client.ClientRegistry.detect_installed_clients", Mock(return_value=installed_clients)
    )

    # Mock client info
    def mock_get_client_info(client_name):
        return {"name": client_name.capitalize(), "download_url": f"https://example.com/{client_name}"}

    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_info", Mock(side_effect=mock_get_client_info))

    # Mock client managers - installed clients return a manager, uninstalled don't
    def mock_get_client_manager(client_name):
        if installed_clients.get(client_name, False):
            mock_manager = Mock()
            mock_manager.get_servers.return_value = {}  # No MCPM servers enabled
            return mock_manager
        return None

    monkeypatch.setattr(
        "mcpm.commands.client.ClientRegistry.get_client_manager", Mock(side_effect=mock_get_client_manager)
    )

    # Run the command
    runner = CliRunner()
    result = runner.invoke(client, ["ls"])

    # Check the result - should show clients with their enabled MCPM servers
    assert result.exit_code == 0
    assert "Found 2 MCP client(s)" in result.output
    assert "Claude-desktop" in result.output
    assert "claude-desktop" in result.output  # Client code in parentheses
    assert "Cursor (cursor)" in result.output
    assert "MCPM Profiles" in result.output
    assert "MCPM Servers" in result.output
    assert "Other Servers" in result.output
    # Windsurf should appear in the "Additional supported clients" section since it's not installed
    assert "Additional supported clients (not detected): Windsurf" in result.output


def test_client_ls_verbose_flag(monkeypatch):
    """Test the 'client ls --verbose' command - should show detailed server information"""
    # Mock supported clients
    supported_clients = ["claude-desktop", "cursor"]
    monkeypatch.setattr(
        "mcpm.commands.client.ClientRegistry.get_supported_clients", Mock(return_value=supported_clients)
    )

    # Mock installed clients
    installed_clients = {"claude-desktop": True, "cursor": True}
    monkeypatch.setattr(
        "mcpm.commands.client.ClientRegistry.detect_installed_clients", Mock(return_value=installed_clients)
    )

    # Mock client info
    def mock_get_client_info(client_name):
        return {"name": client_name.capitalize(), "download_url": f"https://example.com/{client_name}"}

    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_info", Mock(side_effect=mock_get_client_info))

    # Mock client managers with some MCPM servers
    def mock_get_client_manager(client_name):
        mock_manager = Mock()
        if client_name == "claude-desktop":
            # Mock client with one MCPM server
            mock_server_config = Mock()
            mock_server_config.command = "mcpm"
            mock_server_config.args = ["run", "filesystem"]
            mock_manager.get_servers.return_value = {"mcpm_filesystem": mock_server_config}
        else:
            mock_manager.get_servers.return_value = {}
        return mock_manager

    monkeypatch.setattr(
        "mcpm.commands.client.ClientRegistry.get_client_manager", Mock(side_effect=mock_get_client_manager)
    )

    # Mock global config manager for verbose details
    from mcpm.core.schema import STDIOServerConfig

    test_server = STDIOServerConfig(name="filesystem", command="mcp-server-filesystem", args=["/tmp"])
    mock_global_config = Mock()
    mock_global_config.get_server.return_value = test_server
    monkeypatch.setattr("mcpm.commands.client.global_config_manager", mock_global_config)

    # Run the command with --verbose flag
    runner = CliRunner()
    result = runner.invoke(client, ["ls", "--verbose"])

    # Check the result - should show detailed server information
    assert result.exit_code == 0
    assert "Server" in result.output and "Details" in result.output  # Column header may be split
    assert "MCPM Profiles" in result.output
    assert "MCPM Servers" in result.output
    assert "Other Servers" in result.output
    assert "filesystem" in result.output
    # Check for the client name and code (may be truncated due to table formatting)
    assert "Claude-desk" in result.output and "claude-desk" in result.output


def test_client_ls_with_other_servers(monkeypatch):
    """Test the 'client ls' command with both MCPM and other servers"""
    # Mock supported clients
    supported_clients = ["claude-desktop"]
    monkeypatch.setattr(
        "mcpm.commands.client.ClientRegistry.get_supported_clients", Mock(return_value=supported_clients)
    )

    # Mock installed clients
    installed_clients = {"claude-desktop": True}
    monkeypatch.setattr(
        "mcpm.commands.client.ClientRegistry.detect_installed_clients", Mock(return_value=installed_clients)
    )

    # Mock client info
    def mock_get_client_info(client_name):
        return {"name": client_name.capitalize(), "download_url": f"https://example.com/{client_name}"}

    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_info", Mock(side_effect=mock_get_client_info))

    # Mock client manager with both MCPM and other servers
    def mock_get_client_manager(client_name):
        mock_manager = Mock()
        # Create mixed servers: one MCPM server and one other server
        mock_mcpm_server = Mock()
        mock_mcpm_server.command = "mcpm"
        mock_mcpm_server.args = ["run", "filesystem"]

        mock_other_server = {"command": "npx", "args": ["-y", "playwright-server"]}

        mock_manager.get_servers.return_value = {"mcpm_filesystem": mock_mcpm_server, "playwright": mock_other_server}
        return mock_manager

    monkeypatch.setattr(
        "mcpm.commands.client.ClientRegistry.get_client_manager", Mock(side_effect=mock_get_client_manager)
    )

    # Mock global config manager
    mock_global_config = Mock()
    mock_global_config.get_server.return_value = None  # Not needed for this test
    monkeypatch.setattr("mcpm.commands.client.global_config_manager", mock_global_config)

    # Run the command
    runner = CliRunner()
    result = runner.invoke(client, ["ls"])

    # Check the result - should show both MCPM and other servers
    assert result.exit_code == 0
    assert "MCPM Profiles" in result.output
    assert "MCPM Servers" in result.output
    assert "Other Servers" in result.output
    assert "filesystem" in result.output  # MCPM server
    assert "playwright" in result.output  # Other server
    # Check for the client name and code (may be on separate lines due to table formatting)
    assert "Claude-desktop" in result.output and "(claude-desktop)" in result.output


# def test_client_set_command_success(monkeypatch):
#     """Test successful 'client set' command"""
#     # Mock supported clients
#     supported_clients = ["claude-desktop", "windsurf", "cursor"]
#     monkeypatch.setattr(ClientRegistry, "get_supported_clients", Mock(return_value=supported_clients))

#     # Mock active client different from what we're setting
#     monkeypatch.setattr(ClientRegistry, "get_active_client", Mock(return_value="claude-desktop"))

#     # Mock set_active_client to succeed
#     mock_set_active_client = Mock(return_value=True)
#     monkeypatch.setattr(ClientRegistry, "set_active_client", mock_set_active_client)

#     # Run the command
#     runner = CliRunner()
#     result = runner.invoke(set_client, ["windsurf"])

#     # Check the result
#     assert result.exit_code == 0
#     assert "Success" in result.output
#     assert "Active client set to windsurf" in result.output
#     mock_set_active_client.assert_called_once_with("windsurf")


# def test_client_set_command_already_active(monkeypatch):
#     """Test 'client set' when client is already active"""
#     # Mock supported clients
#     supported_clients = ["claude-desktop", "windsurf", "cursor"]
#     monkeypatch.setattr(ClientRegistry, "get_supported_clients", Mock(return_value=supported_clients))

#     # Mock active client same as what we're setting
#     monkeypatch.setattr(ClientRegistry, "get_active_client", Mock(return_value="windsurf"))

#     # Mock set_active_client
#     mock_set_active_client = Mock(return_value=True)
#     monkeypatch.setattr(ClientRegistry, "set_active_client", mock_set_active_client)

#     # Run the command
#     runner = CliRunner()
#     result = runner.invoke(set_client, ["windsurf"])

#     # Check the result
#     assert result.exit_code == 0
#     assert "windsurf is already the active client" in result.output
#     # set_active_client should not be called
#     mock_set_active_client.assert_not_called()


# def test_client_set_command_unsupported(monkeypatch):
#     """Test 'client set' with unsupported client"""
#     # Mock supported clients
#     supported_clients = ["claude-desktop", "windsurf", "cursor"]
#     monkeypatch.setattr(ClientRegistry, "get_supported_clients", Mock(return_value=supported_clients))

#     # Run the command with unsupported client
#     runner = CliRunner()
#     result = runner.invoke(set_client, ["unsupported-client"])

#     # Check the result
#     assert result.exit_code == 0
#     assert "Error" in result.output
#     assert "Unknown client: unsupported-client" in result.output
#     # Verify supported clients are listed
#     for supported_client in supported_clients:
#         assert supported_client in result.output


# def test_client_set_command_failure(monkeypatch):
#     """Test 'client set' when setting fails"""
#     # Mock supported clients
#     supported_clients = ["claude-desktop", "windsurf", "cursor"]
#     monkeypatch.setattr(ClientRegistry, "get_supported_clients", Mock(return_value=supported_clients))

#     # Mock active client different from what we're setting
#     monkeypatch.setattr(ClientRegistry, "get_active_client", Mock(return_value="claude-desktop"))

#     # Mock set_active_client to fail
#     mock_set_active_client = Mock(return_value=False)
#     monkeypatch.setattr(ClientRegistry, "set_active_client", mock_set_active_client)

#     # Run the command
#     runner = CliRunner()
#     result = runner.invoke(set_client, ["windsurf"])

#     # Check the result
#     assert result.exit_code == 0
#     assert "Error" in result.output
#     assert "Failed to set windsurf as the active client" in result.output
#     mock_set_active_client.assert_called_once_with("windsurf")


def test_client_edit_command_client_not_supported(monkeypatch):
    """Test 'client edit' when client is not supported"""
    # Mock client manager to be None (unsupported)
    monkeypatch.setattr(ClientRegistry, "get_client_manager", Mock(return_value=None))
    monkeypatch.setattr(ClientRegistry, "get_supported_clients", Mock(return_value=["cursor", "claude-desktop"]))

    # Run the command with unsupported client
    runner = CliRunner()
    result = runner.invoke(edit_client, ["unsupported-client"])

    # Check the result - should return 0 but print error message
    assert result.exit_code == 0
    assert "Error: Client 'unsupported-client' is not supported." in result.output
    assert "Available clients:" in result.output


def test_client_edit_command_client_not_installed(monkeypatch):
    """Test 'client edit' when client is not installed"""
    # Mock client manager
    mock_client_manager = Mock()
    mock_client_manager.is_client_installed = Mock(return_value=False)
    mock_client_manager.config_path = "/path/to/config.json"

    monkeypatch.setattr(ClientRegistry, "get_client_manager", Mock(return_value=mock_client_manager))
    monkeypatch.setattr(ClientRegistry, "get_client_info", Mock(return_value={"name": "Windsurf"}))

    # Mock GlobalConfigManager - need servers to avoid early exit
    mock_global_config = Mock()
    mock_global_config.list_servers.return_value = {"test-server": Mock(description="Test server")}
    monkeypatch.setattr("mcpm.commands.client.global_config_manager", mock_global_config)

    # Run the command
    runner = CliRunner()
    result = runner.invoke(edit_client, ["windsurf"])

    # Check the result - should show warning but continue with interactive selection
    assert result.exit_code == 0
    assert "⚠️  Windsurf installation not detected." in result.output
    assert "Config file will be created at: /path/to/config.json" in result.output
    assert "You can still configure servers, but make sure to install Windsurf later." in result.output


def test_client_edit_command_config_exists(monkeypatch, tmp_path):
    """Test 'client edit' when config file exists"""
    # Create a temp config file
    config_path = tmp_path / "config.json"
    config_content = json.dumps({"mcpServers": {"test-server": {"command": "test"}}})
    config_path.write_text(config_content)

    # Mock active client manager
    mock_client_manager = Mock()
    mock_client_manager.is_client_installed = Mock(return_value=True)
    mock_client_manager.config_path = str(config_path)

    monkeypatch.setattr(ClientRegistry, "get_client_manager", Mock(return_value=mock_client_manager))
    monkeypatch.setattr(ClientRegistry, "get_client_info", Mock(return_value={"name": "Windsurf"}))

    # Mock GlobalConfigManager - return empty dict to trigger "no servers" path
    mock_global_config = Mock()
    mock_global_config.list_servers = Mock(return_value={})
    monkeypatch.setattr("mcpm.commands.client.global_config_manager", mock_global_config)

    # Run the command
    runner = CliRunner()
    result = runner.invoke(edit_client, ["windsurf"])

    # Check the result - should exit with error due to no servers
    assert result.exit_code == 1
    assert "Windsurf Configuration Management" in result.output
    assert "No servers found in MCPM global configuration" in result.output


def test_client_edit_command_config_not_exists(monkeypatch, tmp_path):
    """Test 'client edit' when config file doesn't exist"""
    # Create a temp config path that doesn't exist yet
    config_path = tmp_path / "config.json"

    # Mock active client manager
    mock_client_manager = Mock()
    mock_client_manager.is_client_installed = Mock(return_value=True)
    mock_client_manager.config_path = str(config_path)

    monkeypatch.setattr(ClientRegistry, "get_client_manager", Mock(return_value=mock_client_manager))
    monkeypatch.setattr(ClientRegistry, "get_client_info", Mock(return_value={"name": "Windsurf"}))

    # Mock GlobalConfigManager - return empty dict to trigger "no servers" path
    mock_global_config = Mock()
    mock_global_config.list_servers = Mock(return_value={})
    monkeypatch.setattr("mcpm.commands.client.global_config_manager", mock_global_config)

    # Run the command
    runner = CliRunner()
    result = runner.invoke(edit_client, ["windsurf"])

    # Check the result - should exit with error due to no servers
    assert result.exit_code == 1
    assert "Windsurf Configuration Management" in result.output
    assert "No servers found in MCPM global configuration" in result.output


def test_client_edit_command_open_editor(monkeypatch, tmp_path):
    """Test 'client edit' with opening editor"""
    # Create a temp config file
    config_path = tmp_path / "config.json"
    config_content = json.dumps({"mcpServers": {"test-server": {"command": "test"}}})
    config_path.write_text(config_content)

    # Mock active client manager
    mock_client_manager = Mock()
    mock_client_manager.is_client_installed = Mock(return_value=True)
    mock_client_manager.config_path = str(config_path)

    monkeypatch.setattr(ClientRegistry, "get_client_manager", Mock(return_value=mock_client_manager))
    monkeypatch.setattr(ClientRegistry, "get_client_info", Mock(return_value={"name": "Windsurf"}))

    # Mock GlobalConfigManager - return some servers to avoid early exit
    mock_global_config = Mock()
    mock_global_config.list_servers = Mock(return_value={"test-server": Mock(description="Test server")})
    monkeypatch.setattr("mcpm.commands.client.global_config_manager", mock_global_config)

    # Force interactive mode to ensure external editor path is taken
    monkeypatch.setattr("mcpm.commands.client.is_non_interactive", lambda: False)
    monkeypatch.setattr("mcpm.commands.client.should_force_operation", lambda: False)

    # Mock the _open_in_editor function to prevent actual editor launching
    with patch("mcpm.commands.client._open_in_editor") as mock_open_editor:
        # Run the command with external editor flag
        runner = CliRunner()
        result = runner.invoke(edit_client, ["windsurf", "--external"])

        # Check the result
        assert result.exit_code == 0
        assert "Windsurf Configuration Management" in result.output
        # Verify that _open_in_editor was called instead of actually opening an editor
        mock_open_editor.assert_called_once_with(str(config_path), "Windsurf")


def test_client_edit_non_interactive_add_server(monkeypatch):
    """Test adding servers to a client non-interactively."""
    # Mock client manager
    mock_client_manager = Mock()
    mock_client_manager.is_client_installed = Mock(return_value=True)
    mock_client_manager.config_path = "/path/to/config.json"
    mock_client_manager.get_servers.return_value = {}
    mock_client_manager.update_servers.return_value = None
    mock_client_manager.add_server.return_value = None

    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_manager", Mock(return_value=mock_client_manager))
    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_info", Mock(return_value={"name": "Cursor"}))

    # Mock GlobalConfigManager
    mock_global_config = Mock()
    mock_global_config.list_servers.return_value = {"test-server": Mock(description="Test server")}
    mock_global_config.get_server.return_value = Mock(name="test-server")
    monkeypatch.setattr("mcpm.commands.client.global_config_manager", mock_global_config)

    # Force non-interactive mode
    monkeypatch.setattr("mcpm.commands.client.is_non_interactive", lambda: True)

    runner = CliRunner()
    result = runner.invoke(edit_client, [
        "cursor",
        "--add-server", "test-server"  # Only add test-server which exists
    ])

    assert result.exit_code == 0
    assert "Successfully updated" in result.output
    
    # Verify that add_server was called with the prefixed server name
    mock_client_manager.add_server.assert_called()
    # Check that add_server was called with a server config for the prefixed server name
    call_args = mock_client_manager.add_server.call_args
    assert call_args is not None
    server_config = call_args[0][0]  # First positional argument
    assert server_config.name == "mcpm_test-server"
    assert server_config.command == "mcpm"
    assert server_config.args == ["run", "test-server"]


def test_client_edit_non_interactive_remove_server(monkeypatch):
    """Test removing servers from a client non-interactively."""
    # Mock client manager with existing server
    mock_client_manager = Mock()
    mock_client_manager.is_client_installed = Mock(return_value=True)
    mock_client_manager.config_path = "/path/to/config.json"
    # Mock an MCPM-managed server in client config
    existing_mcpm_server = Mock()
    existing_mcpm_server.command = "mcpm"
    existing_mcpm_server.args = ["run", "existing-server"]
    mock_client_manager.get_servers.return_value = {"mcpm_existing-server": existing_mcpm_server}
    mock_client_manager.update_servers.return_value = None
    mock_client_manager.remove_server.return_value = None

    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_manager", Mock(return_value=mock_client_manager))
    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_info", Mock(return_value={"name": "Cursor"}))

    # Mock GlobalConfigManager
    mock_global_config = Mock()
    mock_global_config.list_servers.return_value = {"existing-server": Mock(description="Existing server")}
    monkeypatch.setattr("mcpm.commands.client.global_config_manager", mock_global_config)

    # Force non-interactive mode
    monkeypatch.setattr("mcpm.commands.client.is_non_interactive", lambda: True)

    runner = CliRunner()
    result = runner.invoke(edit_client, [
        "cursor",
        "--remove-server", "existing-server"
    ])

    # The command runs without crashing and removes the server
    assert result.exit_code == 0
    assert "Cursor Configuration Management" in result.output
    
    # Verify that remove_server was called with the prefixed server name
    mock_client_manager.remove_server.assert_called_with("mcpm_existing-server")


def test_client_edit_non_interactive_set_servers(monkeypatch):
    """Test setting all servers for a client non-interactively."""
    # Mock client manager
    mock_client_manager = Mock()
    mock_client_manager.is_client_installed = Mock(return_value=True)
    mock_client_manager.config_path = "/path/to/config.json"
    # Return a proper MCPM server configuration that will be recognized
    mock_client_manager.get_servers.return_value = {
        "mcpm_old-server": {
            "command": "mcpm",
            "args": ["run", "old-server"]
        }
    }
    mock_client_manager.add_server.return_value = None
    mock_client_manager.remove_server.return_value = None

    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_manager", Mock(return_value=mock_client_manager))
    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_info", Mock(return_value={"name": "Cursor"}))

    # Mock GlobalConfigManager
    mock_global_config = Mock()
    mock_global_config.list_servers.return_value = {
        "server1": Mock(description="Server 1"),
        "server2": Mock(description="Server 2")
    }
    mock_global_config.get_server.return_value = Mock()
    monkeypatch.setattr("mcpm.commands.client.global_config_manager", mock_global_config)

    # Force non-interactive mode
    monkeypatch.setattr("mcpm.commands.client.is_non_interactive", lambda: True)

    runner = CliRunner()
    result = runner.invoke(edit_client, [
        "cursor",
        "--set-servers", "server1,server2"
    ])

    assert result.exit_code == 0
    assert "Successfully updated" in result.output
    # Verify that add_server was called for the new servers
    assert mock_client_manager.add_server.call_count == 2
    # Verify that remove_server was called for the old server
    mock_client_manager.remove_server.assert_called_with("mcpm_old-server")


def test_client_edit_non_interactive_add_profile(monkeypatch):
    """Test adding profiles to a client non-interactively."""
    # Mock client manager
    mock_client_manager = Mock()
    mock_client_manager.is_client_installed = Mock(return_value=True)
    mock_client_manager.config_path = "/path/to/config.json"
    mock_client_manager.get_servers.return_value = {}
    mock_client_manager.add_server.return_value = None

    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_manager", Mock(return_value=mock_client_manager))
    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_info", Mock(return_value={"name": "Cursor"}))

    # Mock GlobalConfigManager
    mock_global_config = Mock()
    mock_global_config.list_servers.return_value = {"test-server": Mock(description="Test server")}
    monkeypatch.setattr("mcpm.commands.client.global_config_manager", mock_global_config)

    # Mock ProfileConfigManager
    mock_profile_config = Mock()
    mock_profile_config.list_profiles.return_value = {"test-profile": [Mock(name="test-server")]}
    mock_profile_config.get_profile.return_value = [Mock(name="test-server")]
    monkeypatch.setattr("mcpm.profile.profile_config.ProfileConfigManager", lambda: mock_profile_config)

    # Force non-interactive mode
    monkeypatch.setattr("mcpm.commands.client.is_non_interactive", lambda: True)

    runner = CliRunner()
    result = runner.invoke(edit_client, [
        "cursor",
        "--add-profile", "test-profile"
    ])

    assert result.exit_code == 0
    assert "Successfully updated" in result.output
    # Verify that add_server was called for the profile
    assert mock_client_manager.add_server.called


def test_client_edit_non_interactive_server_not_found(monkeypatch):
    """Test error handling when server doesn't exist."""
    # Mock client manager
    mock_client_manager = Mock()
    mock_client_manager.is_client_installed = Mock(return_value=True)
    mock_client_manager.config_path = "/path/to/config.json"
    mock_client_manager.get_servers.return_value = {}

    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_manager", Mock(return_value=mock_client_manager))
    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_info", Mock(return_value={"name": "Cursor"}))

    # Mock GlobalConfigManager with some servers but not the one we're looking for
    mock_global_config = Mock()
    mock_global_config.list_servers.return_value = {"existing-server": Mock(description="Existing server")}
    monkeypatch.setattr("mcpm.commands.client.global_config_manager", mock_global_config)

    # Force non-interactive mode
    monkeypatch.setattr("mcpm.commands.client.is_non_interactive", lambda: True)

    runner = CliRunner()
    result = runner.invoke(edit_client, [
        "cursor",
        "--add-server", "nonexistent-server"
    ])

    assert result.exit_code == 1
    assert "Server(s) not found: nonexistent-server" in result.output


def test_client_edit_with_force_flag(monkeypatch):
    """Test client edit with --force flag."""
    # Mock client manager
    mock_client_manager = Mock()
    mock_client_manager.is_client_installed = Mock(return_value=True)
    mock_client_manager.config_path = "/path/to/config.json"
    mock_client_manager.get_servers.return_value = {}
    mock_client_manager.add_server.return_value = None

    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_manager", Mock(return_value=mock_client_manager))
    monkeypatch.setattr("mcpm.commands.client.ClientRegistry.get_client_info", Mock(return_value={"name": "Cursor"}))

    # Mock GlobalConfigManager
    mock_global_config = Mock()
    mock_global_config.list_servers.return_value = {"test-server": Mock(description="Test server")}
    mock_global_config.get_server.return_value = Mock(name="test-server")
    monkeypatch.setattr("mcpm.commands.client.global_config_manager", mock_global_config)

    runner = CliRunner()
    result = runner.invoke(edit_client, [
        "cursor",
        "--add-server", "test-server",
        "--force"
    ])

    assert result.exit_code == 0
    assert "Successfully updated" in result.output
    # Verify add_server was called for the new server
    assert mock_client_manager.add_server.called


def test_client_edit_command_help():
    """Test the client edit command help output."""
    runner = CliRunner()
    result = runner.invoke(edit_client, ["--help"])

    assert result.exit_code == 0
    assert "Enable/disable MCPM-managed servers" in result.output
    assert "Interactive by default, or use CLI parameters for automation" in result.output
    assert "--add-server" in result.output
    assert "--remove-server" in result.output
    assert "--set-servers" in result.output
    assert "--add-profile" in result.output
    assert "--force" in result.output


def test_main_client_command_help():
    """Test the main client command help output"""
    runner = CliRunner()
    result = runner.invoke(client, ["--help"])

    # Check the result
    assert result.exit_code == 0
    assert "Manage MCP client configurations" in result.output
    # With rich-click, the commands are shown differently
    assert "ls" in result.output
    assert "edit" in result.output
    assert "import" in result.output
