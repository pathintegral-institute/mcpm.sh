from unittest.mock import Mock, patch

from click.testing import CliRunner

from mcpm.clients.client_registry import ClientRegistry
from mcpm.commands.target_operations.remove import remove


def test_remove_server_success(windsurf_manager):
    """Test successful server removal"""

    # Mock server info
    mock_server = Mock()
    mock_server.command = "npx"
    mock_server.args = ["-y", "@modelcontextprotocol/server-test"]
    mock_server.env = {"API_KEY": "test-key"}
    windsurf_manager.get_server = Mock(return_value=mock_server)
    windsurf_manager.remove_server = Mock(return_value=True)

    # Run the command with force flag to skip confirmation
    runner = CliRunner()
    result = runner.invoke(remove, ["server-test", "--force"])

    assert result.exit_code == 0
    assert "Successfully removed server: server-test" in result.output
    windsurf_manager.remove_server.assert_called_once_with("server-test")


def test_remove_server_not_found(windsurf_manager):
    """Test removal of non-existent server"""
    # Mock server not found
    windsurf_manager.get_server = Mock(return_value=None)

    # Run the command with force flag
    runner = CliRunner()
    result = runner.invoke(remove, ["server-test", "--force"])

    assert result.exit_code == 0  # Command exits successfully but with error message
    assert "Server 'server-test' not found in windsurf" in result.output

    # Mock server not found
    windsurf_manager.get_server = Mock(return_value=None)

    runner = CliRunner()
    result = runner.invoke(remove, ["non-existent-server"])

    assert result.exit_code == 0  # Command exits successfully but with error message
    assert "Server 'non-existent-server' not found in windsurf" in result.output


def test_remove_server_unsupported_client(monkeypatch):
    """Test removal with unsupported client"""
    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=None))
    monkeypatch.setattr(ClientRegistry, "get_active_target", Mock(return_value="@unsupported"))

    runner = CliRunner()
    result = runner.invoke(remove, ["server-test"])

    assert result.exit_code == 0  # Command exits successfully but with error message
    assert "Client 'unsupported' not found." in result.output


def test_remove_server_cancelled(windsurf_manager):
    """Test removal when user cancels the confirmation"""

    # Mock server info
    mock_server = Mock()
    mock_server.command = "npx"
    mock_server.args = ["-y", "@modelcontextprotocol/server-test"]
    mock_server.env = {"API_KEY": "test-key"}
    windsurf_manager.get_server = Mock(return_value=mock_server)
    windsurf_manager.remove_server = Mock(return_value=True)

    # Run the command without force flag and simulate user cancellation
    runner = CliRunner()
    with patch("rich.prompt.Confirm.ask", return_value=False):
        result = runner.invoke(remove, ["server-test"])

    assert result.exit_code == 0
    assert "Removal cancelled" in result.output
    windsurf_manager.remove_server.assert_not_called()


def test_remove_server_failure(windsurf_manager):
    """Test removal when the removal operation fails"""

    # Mock server info
    mock_server = Mock()
    mock_server.command = "npx"
    mock_server.args = ["-y", "@modelcontextprotocol/server-test"]
    mock_server.env = {"API_KEY": "test-key"}
    windsurf_manager.get_server = Mock(return_value=mock_server)
    windsurf_manager.remove_server = Mock(return_value=False)

    # Run the command with force flag
    runner = CliRunner()
    result = runner.invoke(remove, ["server-test", "--force"])

    assert result.exit_code == 0  # Command exits successfully but with error message
    assert "Failed to remove server 'server-test'" in result.output
    windsurf_manager.remove_server.assert_called_once_with("server-test")
