from unittest.mock import Mock

from click.testing import CliRunner

from mcpm.clients.client_registry import ClientRegistry
from mcpm.commands.add import add
from mcpm.utils.repository import RepositoryManager


def test_add_server(windsurf_manager, monkeypatch):
    """Test add server"""
    monkeypatch.setattr(ClientRegistry, "get_active_client", Mock(return_value="windsurf"))
    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=windsurf_manager))
    monkeypatch.setattr(
        RepositoryManager,
        "_fetch_servers",
        Mock(
            return_value={
                "server-test": {
                    "installations": {
                        "npm": {
                            "type": "npm",
                            "command": "npx",
                            "args": ["-y", "@modelcontextprotocol/server-test", "--fmt", "${fmt}"],
                            "env": {"API_KEY": "${API_KEY}"},
                        }
                    },
                    "arguments": {
                        "fmt": {"type": "string", "description": "Output format", "required": True},
                        "API_KEY": {"type": "string", "description": "API key", "required": True},
                    },
                }
            }
        ),
    )
    runner = CliRunner()
    result = runner.invoke(add, ["server-test", "--force", "--alias", "test"], input="\njson\n\ntest-api-key\n")
    assert result.exit_code == 0

    # Check that the server was added
    server = windsurf_manager.get_server("test")
    assert server is not None
    assert server.command == "npx"
    assert server.args == ["-y", "@modelcontextprotocol/server-test", "--fmt", "json"]
    assert server.env["API_KEY"] == "test-api-key"
