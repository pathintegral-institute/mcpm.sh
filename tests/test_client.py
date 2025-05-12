"""
Tests for the client commands (ls, set, edit)
"""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from mcpm.clients.client_registry import ClientRegistry
from mcpm.commands.client import client, edit_client, list_clients


def test_client_ls_command(monkeypatch):
    """Test the 'client ls' command"""
    # Mock supported clients
    supported_clients = ["claude-desktop", "windsurf", "cursor"]
    monkeypatch.setattr(ClientRegistry, "get_supported_clients", Mock(return_value=supported_clients))

    # Mock active client
    monkeypatch.setattr(ClientRegistry, "get_active_client", Mock(return_value="claude-desktop"))

    # Mock installed clients
    installed_clients = {"claude-desktop": True, "windsurf": False, "cursor": True}
    monkeypatch.setattr(ClientRegistry, "detect_installed_clients", Mock(return_value=installed_clients))

    # Mock client info
    def mock_get_client_info(client_name):
        return {"name": client_name.capitalize(), "download_url": f"https://example.com/{client_name}"}

    monkeypatch.setattr(ClientRegistry, "get_client_info", Mock(side_effect=mock_get_client_info))

    # Run the command
    runner = CliRunner()
    result = runner.invoke(list_clients)

    # Check the result
    assert result.exit_code == 0
    assert "Supported MCP Clients" in result.output
    assert "Claude-desktop" in result.output
    assert "Windsurf" in result.output
    assert "Cursor" in result.output
    assert "ACTIVE" in result.output
    assert "Installed" in result.output
    assert "Not installed" in result.output


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
    # Mock active client manager to be None (unsupported)
    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=None))
    monkeypatch.setattr(ClientRegistry, "get_active_client", Mock(return_value="unsupported"))
    monkeypatch.setattr(ClientRegistry, "get_client_info", Mock(return_value={"name": "Unsupported"}))

    # Mock print_client_error
    with patch("mcpm.commands.client.print_client_error") as mock_print_error:
        # Run the command
        runner = CliRunner()
        result = runner.invoke(edit_client)

        # Check the result
        assert result.exit_code == 0
        mock_print_error.assert_called_once_with()


def test_client_edit_command_client_not_installed(monkeypatch):
    """Test 'client edit' when client is not installed"""
    # Mock active client manager
    mock_client_manager = Mock()
    mock_client_manager.is_client_installed = Mock(return_value=False)
    mock_client_manager.config_path = "/path/to/config.json"

    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=mock_client_manager))
    monkeypatch.setattr(ClientRegistry, "get_active_client", Mock(return_value="windsurf"))
    monkeypatch.setattr(ClientRegistry, "get_client_info", Mock(return_value={"name": "Windsurf"}))

    # Mock print_error
    with patch("mcpm.commands.client.print_error") as mock_print_error:
        # Run the command
        runner = CliRunner()
        result = runner.invoke(edit_client)

        # Check the result
        assert result.exit_code == 0
        mock_print_error.assert_called_once_with("Windsurf installation not detected.")


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

    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=mock_client_manager))
    monkeypatch.setattr(ClientRegistry, "get_active_client", Mock(return_value="windsurf"))
    monkeypatch.setattr(ClientRegistry, "get_client_info", Mock(return_value={"name": "Windsurf"}))

    # Mock Confirm.ask to return False (don't open editor)
    with patch("mcpm.commands.client.Confirm.ask", Mock(return_value=False)):
        # Run the command
        runner = CliRunner()
        result = runner.invoke(edit_client)

        # Check the result
        assert result.exit_code == 0
        assert "Windsurf config file" in result.output
        assert "Current configuration" in result.output
        assert "Configured servers: 1" in result.output


def test_client_edit_command_config_not_exists(monkeypatch, tmp_path):
    """Test 'client edit' when config file doesn't exist"""
    # Create a temp config path that doesn't exist yet
    config_path = tmp_path / "config.json"

    # Mock active client manager
    mock_client_manager = Mock()
    mock_client_manager.is_client_installed = Mock(return_value=True)
    mock_client_manager.config_path = str(config_path)

    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=mock_client_manager))
    monkeypatch.setattr(ClientRegistry, "get_active_client", Mock(return_value="windsurf"))
    monkeypatch.setattr(ClientRegistry, "get_client_info", Mock(return_value={"name": "Windsurf"}))

    # Run the command with custom input
    runner = CliRunner()

    # Mock os.makedirs to prevent actual directory creation
    with (
        patch("os.makedirs"),
        patch("builtins.open", Mock()),
        patch("json.dump", Mock()),
        patch("mcpm.commands.client.Confirm.ask", Mock(return_value=False)),
    ):
        result = runner.invoke(edit_client)

        # Check the result
        assert result.exit_code == 0
        assert "Windsurf config file" in result.output
        assert "Creating new Windsurf config file" in result.output


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

    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=mock_client_manager))
    monkeypatch.setattr(ClientRegistry, "get_active_client", Mock(return_value="windsurf"))
    monkeypatch.setattr(ClientRegistry, "get_client_info", Mock(return_value={"name": "Windsurf"}))

    # Mock Confirm.ask to return True (open editor)
    with (
        patch("mcpm.commands.client.Confirm.ask", Mock(return_value=True)),
        patch("mcpm.commands.client.subprocess.run") as mock_run,
        patch("os.name", "posix"),
        patch("os.uname", Mock(return_value=Mock(sysname="Darwin"))),
    ):
        # Run the command
        runner = CliRunner()
        result = runner.invoke(edit_client)

        # Check the result
        assert result.exit_code == 0
        assert "Opening config file in your default editor" in result.output
        mock_run.assert_called_once_with(["open", str(config_path)])


def test_main_client_command_help():
    """Test the main client command help output"""
    runner = CliRunner()
    result = runner.invoke(client, ["--help"])

    # Check the result
    assert result.exit_code == 0
    assert "Manage MCP clients" in result.output
    assert "Commands:" in result.output
    assert "ls" in result.output
    assert "set" in result.output
    assert "edit" in result.output
