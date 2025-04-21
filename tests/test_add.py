from unittest.mock import Mock, patch

from click.testing import CliRunner

from mcpm.clients.client_registry import ClientRegistry
from mcpm.commands.server_operations.add import add
from mcpm.schemas.server_config import SSEServerConfig
from mcpm.utils.repository import RepositoryManager


def test_add_server(windsurf_manager, monkeypatch):
    """Test add server"""
    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=windsurf_manager))
    monkeypatch.setattr(ClientRegistry, "get_client_manager", Mock(return_value=windsurf_manager))
    monkeypatch.setattr(ClientRegistry, "determine_active_scope", Mock(return_value="@windsurf"))
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
    """Test add server with a missing argument that should be replaced with empty string"""
    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=windsurf_manager))
    monkeypatch.setattr(ClientRegistry, "get_client_manager", Mock(return_value=windsurf_manager))
    monkeypatch.setattr(ClientRegistry, "determine_active_scope", Mock(return_value="@windsurf"))
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
                        # Deliberately not including TZ to test empty string replacement
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

    # Check that the server was added with alias and the missing argument is replaced with empty string
    server = windsurf_manager.get_server("test-missing-arg")
    assert server is not None
    assert server.command == "npx"
    # The ${TZ} argument should be replaced with empty string since it's not in processed variables
    assert server.args == ["-y", "@modelcontextprotocol/server-test", "--fmt", "json", "--timezone", ""]
    assert server.env["API_KEY"] == "test-api-key"


def test_add_server_with_empty_args(windsurf_manager, monkeypatch):
    """Test add server with missing arguments that should be replaced with empty strings"""
    monkeypatch.setattr(ClientRegistry, "get_active_client", Mock(return_value="windsurf"))
    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=windsurf_manager))
    monkeypatch.setattr(ClientRegistry, "get_client_manager", Mock(return_value=windsurf_manager))
    monkeypatch.setattr(ClientRegistry, "determine_active_scope", Mock(return_value="@windsurf"))
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
                                "--optional",
                                "${OPTIONAL}",  # Optional arg not in arguments list
                                "--api-key",
                                "${API_KEY}",
                            ],
                            "env": {
                                "API_KEY": "${API_KEY}",
                                "OPTIONAL_ENV": "${OPTIONAL}",  # Optional env var
                            },
                        }
                    },
                    "arguments": {
                        "fmt": {"type": "string", "description": "Output format", "required": True},
                        "API_KEY": {"type": "string", "description": "API key", "required": True},
                        # OPTIONAL is not listed in arguments
                    },
                }
            }
        ),
    )

    # Mock prompt responses for required arguments only
    with (
        patch("prompt_toolkit.PromptSession.prompt", side_effect=["json", "test-api-key"]),
        patch("rich.progress.Progress.start"),
        patch("rich.progress.Progress.stop"),
        patch("rich.progress.Progress.add_task"),
    ):
        runner = CliRunner(mix_stderr=False)
        result = runner.invoke(add, ["server-test", "--force", "--alias", "test-empty-args"])

        assert result.exit_code == 0

    # Check that the server was added and optional arguments are empty
    server = windsurf_manager.get_server("test-empty-args")
    assert server is not None
    assert server.command == "npx"
    # Optional arguments should be replaced with empty strings
    assert server.args == [
        "-y",
        "@modelcontextprotocol/server-test",
        "--fmt",
        "json",
        "--optional",
        "",  # ${OPTIONAL} replaced with empty string
        "--api-key",
        "test-api-key",
    ]
    assert server.env == {
        "API_KEY": "test-api-key",
        "OPTIONAL_ENV": "",  # Optional env var should be empty string
    }


def test_add_sse_server_to_claude_desktop(claude_desktop_manager, monkeypatch):
    """Test add sse server to claude desktop"""
    server_config = SSEServerConfig(
        name="test-sse-server", url="http://localhost:8080", headers={"Authorization": "Bearer test-api-key"}
    )
    claude_desktop_manager.add_server(server_config)
    stored_config = claude_desktop_manager.get_server("test-sse-server")
    assert stored_config is not None
    assert stored_config.name == "test-sse-server"
    assert stored_config.command == "uvx"
    assert stored_config.args == [
        "mcp-proxy",
        "http://localhost:8080",
        "--headers",
        "Authorization",
        "Bearer test-api-key",
    ]
