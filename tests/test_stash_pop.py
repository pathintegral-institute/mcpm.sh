from unittest.mock import Mock

from click.testing import CliRunner

from mcpm.clients.client_registry import ClientRegistry
from mcpm.commands.target_operations.pop import pop
from mcpm.commands.target_operations.stash import stash


def test_stash_server_success(windsurf_manager, monkeypatch):
    """Test successful server stashing"""
    # Mock server info
    mock_server = Mock()
    mock_server.command = "npx"
    mock_server.args = ["-y", "@modelcontextprotocol/server-test"]
    mock_server.env = {"API_KEY": "test-key"}
    mock_server.to_dict = Mock(
        return_value={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-test"],
            "env": {"API_KEY": "test-key"},
        }
    )
    windsurf_manager.get_server = Mock(return_value=mock_server)
    windsurf_manager.remove_server = Mock(return_value=True)

    # Mock client config manager
    mock_config_manager = Mock()
    mock_config_manager.is_server_stashed = Mock(return_value=False)
    mock_config_manager.stash_server = Mock(return_value=True)
    mock_config_manager.pop_server = Mock()  # Not called in success case
    monkeypatch.setattr("mcpm.commands.stash.client_config_manager", mock_config_manager)

    # Run the command
    runner = CliRunner()
    result = runner.invoke(stash, ["server-test"])

    assert result.exit_code == 0
    assert "Stashed MCP server 'server-test' for windsurf" in result.output
    mock_config_manager.stash_server.assert_called_once()
    windsurf_manager.remove_server.assert_called_once_with("server-test")


def test_stash_server_already_stashed(windsurf_manager, monkeypatch):
    """Test stashing an already stashed server"""

    # Mock server info
    mock_server = Mock()
    mock_server.command = "npx"
    windsurf_manager.get_server = Mock(return_value=mock_server)

    # Mock client config manager
    mock_config_manager = Mock()
    mock_config_manager.is_server_stashed = Mock(return_value=True)
    monkeypatch.setattr("mcpm.commands.stash.client_config_manager", mock_config_manager)

    runner = CliRunner()
    result = runner.invoke(stash, ["server-test"])

    assert result.exit_code == 0
    assert "Server 'server-test' is already stashed for windsurf" in result.output
    mock_config_manager.stash_server.assert_not_called()


def test_stash_server_remove_failure(windsurf_manager, monkeypatch):
    """Test stashing when server removal fails"""
    # Mock server info
    mock_server = Mock()
    mock_server.command = "npx"
    mock_server.to_dict = Mock(return_value={"command": "npx"})
    windsurf_manager.get_server = Mock(return_value=mock_server)
    windsurf_manager.remove_server = Mock(return_value=False)

    # Mock client config manager
    mock_config_manager = Mock()
    mock_config_manager.is_server_stashed = Mock(return_value=False)
    mock_config_manager.stash_server = Mock(return_value=True)
    mock_config_manager.pop_server = Mock()
    monkeypatch.setattr("mcpm.commands.stash.client_config_manager", mock_config_manager)

    runner = CliRunner()
    result = runner.invoke(stash, ["server-test"])

    assert result.exit_code == 0
    assert "Failed to remove server from windsurf" in result.output
    mock_config_manager.pop_server.assert_called_once()


def test_stash_server_not_found(windsurf_manager, monkeypatch):
    """Test stashing a non-existent server"""
    # Mock server not found
    windsurf_manager.get_server = Mock(return_value=None)

    # Mock client config manager
    mock_config_manager = Mock()
    mock_config_manager.is_server_stashed = Mock(return_value=False)
    monkeypatch.setattr("mcpm.commands.stash.client_config_manager", mock_config_manager)

    runner = CliRunner()
    result = runner.invoke(stash, ["non-existent-server"])

    assert result.exit_code == 0
    assert "Server 'non-existent-server' not found in windsurf" in result.output
    mock_config_manager.stash_server.assert_not_called()


def test_stash_server_unsupported_client(monkeypatch):
    """Test stashing with unsupported client"""
    monkeypatch.setattr(ClientRegistry, "get_active_target", Mock(return_value="@unsupported"))
    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=None))

    # Mock client config manager
    mock_config_manager = Mock()
    monkeypatch.setattr("mcpm.commands.stash.client_config_manager", mock_config_manager)

    runner = CliRunner()
    result = runner.invoke(stash, ["server-test"])

    assert result.exit_code == 0
    assert "Client 'unsupported' not found." in result.output
    mock_config_manager.stash_server.assert_not_called()


def test_pop_server_success(windsurf_manager, monkeypatch):
    """Test successful server restoration"""
    # Mock server data
    server_data = {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-test"],
        "env": {"API_KEY": "test-key"},
    }

    # Mock client config manager
    mock_config_manager = Mock()
    mock_config_manager.is_server_stashed = Mock(return_value=True)
    mock_config_manager.pop_server = Mock(return_value=server_data)
    mock_config_manager.stash_server = Mock()  # Not called in success case
    monkeypatch.setattr("mcpm.commands.pop.client_config_manager", mock_config_manager)

    # Mock client manager
    mock_server_config = Mock()
    windsurf_manager.from_client_format = Mock(return_value=mock_server_config)
    windsurf_manager.add_server = Mock(return_value=True)

    runner = CliRunner()
    result = runner.invoke(pop, ["server-test"])

    assert result.exit_code == 0
    assert "Restored MCP server 'server-test' for windsurf" in result.output
    mock_config_manager.pop_server.assert_called_once_with("@windsurf", "server-test")
    windsurf_manager.add_server.assert_called_once_with(mock_server_config)


def test_pop_server_not_stashed(windsurf_manager, monkeypatch):
    """Test popping a non-stashed server"""
    # Mock client config manager
    mock_config_manager = Mock()
    mock_config_manager.is_server_stashed = Mock(return_value=False)
    monkeypatch.setattr("mcpm.commands.pop.client_config_manager", mock_config_manager)

    runner = CliRunner()
    result = runner.invoke(pop, ["server-test"])

    assert result.exit_code == 0
    assert "Server 'server-test' not found in stashed configurations for windsurf" in result.output
    mock_config_manager.pop_server.assert_not_called()


def test_pop_server_add_failure(windsurf_manager, monkeypatch):
    """Test popping when server addition fails"""

    # Mock server data
    server_data = {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-test"],
        "env": {"API_KEY": "test-key"},
    }

    # Mock client config manager
    mock_config_manager = Mock()
    mock_config_manager.is_server_stashed = Mock(return_value=True)
    mock_config_manager.pop_server = Mock(return_value=server_data)
    mock_config_manager.stash_server = Mock(return_value=True)
    monkeypatch.setattr("mcpm.commands.pop.client_config_manager", mock_config_manager)

    # Mock client manager
    mock_server_config = Mock()
    windsurf_manager.from_client_format = Mock(return_value=mock_server_config)
    windsurf_manager.add_server = Mock(return_value=False)

    runner = CliRunner()
    result = runner.invoke(pop, ["server-test"])

    assert result.exit_code == 0
    assert "Failed to restore 'server-test' for Windsurf" in result.output
    mock_config_manager.stash_server.assert_called_once_with("@windsurf", "server-test", server_data)


def test_pop_server_unsupported_client(monkeypatch):
    """Test popping with unsupported client"""
    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=None))
    monkeypatch.setattr(ClientRegistry, "get_active_target", Mock(return_value="@unsupported"))

    # Mock client config manager
    mock_config_manager = Mock()
    monkeypatch.setattr("mcpm.commands.pop.client_config_manager", mock_config_manager)

    runner = CliRunner()
    result = runner.invoke(pop, ["server-test"])

    assert result.exit_code == 0

    assert "Unsupported active client" in result.output
    # pop and revert
    mock_config_manager.pop_server.assert_called_once()
    mock_config_manager.stash_server.assert_not_called()
