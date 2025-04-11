from unittest.mock import Mock, patch

from click.testing import CliRunner

from mcpm.clients.client_registry import ClientRegistry
from mcpm.commands.server_operations.add import add
from mcpm.utils.repository import RepositoryManager


def test_add_server(windsurf_manager, monkeypatch):
    """Test add server"""
    monkeypatch.setattr(ClientRegistry, "get_active_client", Mock(return_value="windsurf"))
    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=windsurf_manager))
    monkeypatch.setattr(ClientRegistry, "get_client_manager", Mock(return_value=windsurf_manager))
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

    # Mock prompt_toolkit's prompt to return our test values
    with patch("prompt_toolkit.PromptSession.prompt", side_effect=["json", "test-api-key"]):
        runner = CliRunner()
        result = runner.invoke(add, ["server-test", "--force", "--alias", "test"])
        assert result.exit_code == 0

    # Check that the server was added with alias
    server = windsurf_manager.get_server("test")
    assert server is not None
    assert server.command == "npx"
    assert server.args == ["-y", "@modelcontextprotocol/server-test", "--fmt", "json"]
    assert server.env["API_KEY"] == "test-api-key"


def test_add_server_with_missing_arg(windsurf_manager, monkeypatch):
    """Test add server with a missing argument that should remain in the args"""
    monkeypatch.setattr(ClientRegistry, "get_active_client", Mock(return_value="windsurf"))
    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=windsurf_manager))
    monkeypatch.setattr(ClientRegistry, "get_client_manager", Mock(return_value=windsurf_manager))
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
                            "args": [
                                "-y",
                                "@modelcontextprotocol/server-test",
                                "--fmt",
                                "${fmt}",
                                "--timezone",
                                "${TZ}",  # TZ is not in the arguments list
                            ],
                            "env": {"API_KEY": "${API_KEY}"},
                        }
                    },
                    "arguments": {
                        "fmt": {"type": "string", "description": "Output format", "required": True},
                        "API_KEY": {"type": "string", "description": "API key", "required": True},
                        # Deliberately not including TZ to test the bug fix
                    },
                }
            }
        ),
    )

    # Instead of mocking Console and Progress, we'll mock key methods directly
    # This is a simpler approach that avoids complex mock setup
    with (
        patch("prompt_toolkit.PromptSession.prompt", side_effect=["json", "test-api-key"]),
        patch("rich.progress.Progress.start"),
        patch("rich.progress.Progress.stop"),
        patch("rich.progress.Progress.add_task"),
    ):
        # Use CliRunner which provides its own isolated environment
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(add, ["server-test", "--force", "--alias", "test-missing-arg"])

        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Exception: {result.exception}")
            print(f"Output: {result.stdout}")

        assert result.exit_code == 0

    # Check that the server was added with alias and the missing argument is preserved
    server = windsurf_manager.get_server("test-missing-arg")
    assert server is not None
    assert server.command == "npx"
    # The ${TZ} argument should remain intact since it's not in the processed variables
    assert server.args == ["-y", "@modelcontextprotocol/server-test", "--fmt", "json", "--timezone", "${TZ}"]
    assert server.env["API_KEY"] == "test-api-key"
