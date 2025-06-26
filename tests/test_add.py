from unittest.mock import Mock, patch

from click.testing import CliRunner

from mcpm.commands.target_operations.add import add
from mcpm.core.schema import RemoteServerConfig
from mcpm.utils.config import ConfigManager
from mcpm.utils.repository import RepositoryManager


def test_add_server(windsurf_manager, monkeypatch):
    """Test add server"""
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
        runner = CliRunner()
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
        runner = CliRunner()
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
    server_config = RemoteServerConfig(
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


def test_add_profile_to_client(windsurf_manager, monkeypatch):
    profile_name = "work"
    monkeypatch.setattr(ConfigManager, "get_router_config", Mock(return_value={"host": "localhost", "port": 8080}))

    # test cli
    runner = CliRunner()
    result = runner.invoke(add, ["%" + profile_name, "--force", "--alias", "work"])
    assert result.exit_code == 0
    assert "Successfully added profile work to windsurf!" in result.output

    profile_server = windsurf_manager.get_server("work")
    assert profile_server is not None


def test_add_server_with_configured_npx(windsurf_manager, monkeypatch):
    monkeypatch.setattr(ConfigManager, "get_config", Mock(return_value={"node_executable": "bunx"}))
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

    # Mock Rich's progress display to prevent 'Only one live display may be active at once' error
    with patch("rich.progress.Progress.__enter__", return_value=Mock()), \
         patch("rich.progress.Progress.__exit__"), \
         patch("prompt_toolkit.PromptSession.prompt", side_effect=["json", "test-api-key"]):
        runner = CliRunner()
        result = runner.invoke(add, ["server-test", "--force", "--alias", "test"])
        assert result.exit_code == 0

    # Check that the server was added with alias
    server = windsurf_manager.get_server("test")
    assert server is not None
    # Should use configured node executable
    assert server.command == "bunx"
    assert server.args == ["-y", "@modelcontextprotocol/server-test", "--fmt", "json"]
    assert server.env["API_KEY"] == "test-api-key"
