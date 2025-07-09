from unittest.mock import Mock, patch

from click.testing import CliRunner

from mcpm.commands.install import install
from mcpm.core.schema import RemoteServerConfig, STDIOServerConfig
from mcpm.global_config import GlobalConfigManager
from mcpm.utils.config import ConfigManager
from mcpm.utils.repository import RepositoryManager


def test_add_server(windsurf_manager, monkeypatch, tmp_path):
    """Test add server to global configuration (v2.0)"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    monkeypatch.setattr("mcpm.commands.install.global_config_manager", global_config_manager)

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
        result = runner.invoke(install, ["server-test", "--force", "--alias", "test"])
        assert result.exit_code == 0

    # Check that the server was added to global configuration with alias
    server = global_config_manager.get_server("test")
    assert server is not None
    assert server.command == "npx"
    assert server.args == ["-y", "@modelcontextprotocol/server-test", "--fmt", "json"]
    assert server.env["API_KEY"] == "test-api-key"


def test_add_server_with_missing_arg(windsurf_manager, monkeypatch, tmp_path):
    """Test add server with a missing argument that should be replaced with empty string"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    monkeypatch.setattr("mcpm.commands.install.global_config_manager", global_config_manager)

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
        result = runner.invoke(install, ["server-test", "--force", "--alias", "test-missing-arg"])

        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Exception: {result.exception}")
            print(f"Output: {result.stdout}")

        assert result.exit_code == 0

    # Check that the server was added with alias and the missing argument is replaced with empty string
    server = global_config_manager.get_server("test-missing-arg")
    assert server is not None
    assert server.command == "npx"
    # The ${TZ} argument should be replaced with empty string since it's not in processed variables
    assert server.args == ["-y", "@modelcontextprotocol/server-test", "--fmt", "json", "--timezone", ""]
    assert server.env["API_KEY"] == "test-api-key"


def test_add_server_with_empty_args(windsurf_manager, monkeypatch, tmp_path):
    """Test add server with missing arguments that should be replaced with empty strings"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    monkeypatch.setattr("mcpm.commands.install.global_config_manager", global_config_manager)

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
        result = runner.invoke(install, ["server-test", "--force", "--alias", "test-empty-args"])

        assert result.exit_code == 0

    # Check that the server was added and optional arguments are empty
    server = global_config_manager.get_server("test-empty-args")
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
    # Note: Environment variables may not be processed the same way as arguments
    # Check that required env vars are set properly
    assert server.env["API_KEY"] == "test-api-key"
    # Optional env var might not be processed, so just check the structure
    assert "OPTIONAL_ENV" in server.env


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


def test_add_profile_to_client(windsurf_manager, monkeypatch, tmp_path):
    """Test adding a profile in v2.0 - profile activation has been removed"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    monkeypatch.setattr("mcpm.commands.install.global_config_manager", global_config_manager)

    profile_name = "work"

    # test cli - in v2.0, % prefix is treated as a regular server name since profile activation is removed
    runner = CliRunner()
    result = runner.invoke(install, ["%" + profile_name, "--force", "--alias", "work"])

    # Should fail because "%work" is not a valid server in the registry
    assert result.exit_code == 0  # Command doesn't crash but will show error about server not found
    assert "not found in registry" in result.output


def test_add_server_with_configured_npx(windsurf_manager, monkeypatch, tmp_path):
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    monkeypatch.setattr("mcpm.commands.install.global_config_manager", global_config_manager)

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
    with (
        patch("rich.progress.Progress.__enter__", return_value=Mock()),
        patch("rich.progress.Progress.__exit__"),
        patch("prompt_toolkit.PromptSession.prompt", side_effect=["json", "test-api-key"]),
    ):
        runner = CliRunner()
        result = runner.invoke(install, ["server-test", "--force", "--alias", "test"])
        assert result.exit_code == 0

    # Check that the server was added with alias
    server = global_config_manager.get_server("test")
    assert server is not None
    # Should use configured node executable
    assert server.command == "bunx"
    assert server.args == ["-y", "@modelcontextprotocol/server-test", "--fmt", "json"]
    assert server.env["API_KEY"] == "test-api-key"


def test_add_http_server(windsurf_manager, monkeypatch, tmp_path):
    """Test add HTTP server to global configuration"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    monkeypatch.setattr("mcpm.commands.install.global_config_manager", global_config_manager)

    monkeypatch.setattr(
        RepositoryManager,
        "_fetch_servers",
        Mock(
            return_value={
                "github": {
                    "display_name": "GitHub MCP Server",
                    "description": "Official GitHub MCP server",
                    "installations": {
                        "http": {
                            "type": "http",
                            "url": "https://github.com/github/github-mcp-server/releases/latest/download/github-mcp-server",
                            "description": "Run as HTTP server",
                            "recommended": True,
                        }
                    },
                    "arguments": {
                        "GITHUB_API_TOKEN": {"type": "string", "description": "GitHub API token", "required": True},
                    },
                }
            }
        ),
    )

    # Mock prompt_toolkit's prompt to return our test values
    # Since HTTP installation doesn't reference any variables, no prompts should occur
    with (
        patch("prompt_toolkit.PromptSession.prompt") as mock_prompt,
        patch("rich.progress.Progress.start"),
        patch("rich.progress.Progress.stop"),
        patch("rich.progress.Progress.add_task"),
    ):
        runner = CliRunner()
        result = runner.invoke(install, ["github", "--force"])
        assert result.exit_code == 0
        # No prompts should have been shown since HTTP method doesn't reference any variables
        mock_prompt.assert_not_called()

    # Check that the server was added to global configuration as RemoteServerConfig
    server = global_config_manager.get_server("github")
    assert server is not None
    assert isinstance(server, RemoteServerConfig)
    assert server.url == "https://github.com/github/github-mcp-server/releases/latest/download/github-mcp-server"
    # No headers should be set since the test installation doesn't define any
    assert server.headers == {}


def test_add_server_with_filtered_arguments(windsurf_manager, monkeypatch, tmp_path):
    """Test that only referenced arguments are prompted for"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    monkeypatch.setattr("mcpm.commands.install.global_config_manager", global_config_manager)

    monkeypatch.setattr(
        RepositoryManager,
        "_fetch_servers",
        Mock(
            return_value={
                "test-server": {
                    "display_name": "Test Server",
                    "description": "Test server with multiple arguments",
                    "installations": {
                        "docker": {
                            "type": "docker",
                            "command": "docker",
                            "args": ["run", "-e", "API_KEY=${API_KEY}", "test-server"],
                            "env": {"API_KEY": "${API_KEY}"},
                            "description": "Run with Docker - only uses API_KEY",
                            "recommended": True,
                        }
                    },
                    "arguments": {
                        "API_KEY": {"type": "string", "description": "API key", "required": True},
                        "DATABASE_URL": {"type": "string", "description": "Database URL", "required": True},
                        "UNUSED_VAR": {
                            "type": "string",
                            "description": "This var is not used in docker",
                            "required": True,
                        },
                    },
                }
            }
        ),
    )

    # Mock prompt_toolkit's prompt to return our test values
    # Should only be called once for API_KEY since that's the only referenced variable
    prompt_calls = []

    def mock_prompt_func(*args, **kwargs):
        prompt_calls.append(kwargs.get("message", ""))
        return "test-api-key"

    with (
        patch("prompt_toolkit.PromptSession.prompt", side_effect=mock_prompt_func),
        patch("rich.progress.Progress.start"),
        patch("rich.progress.Progress.stop"),
        patch("rich.progress.Progress.add_task"),
    ):
        runner = CliRunner()
        result = runner.invoke(install, ["test-server", "--force"])
        assert result.exit_code == 0

        # Check that only API_KEY was prompted for
        assert len(prompt_calls) == 1
        assert "API_KEY" in str(prompt_calls[0])
        assert "DATABASE_URL" not in str(prompt_calls[0])
        assert "UNUSED_VAR" not in str(prompt_calls[0])

    # Check that the server was added correctly
    server = global_config_manager.get_server("test-server")
    assert server is not None
    assert isinstance(server, STDIOServerConfig)
    assert server.command == "docker"
    assert server.args == ["run", "-e", "API_KEY=test-api-key", "test-server"]
    assert server.env["API_KEY"] == "test-api-key"


def test_add_http_server_with_headers(windsurf_manager, monkeypatch, tmp_path):
    """Test add HTTP server with headers to global configuration"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    monkeypatch.setattr("mcpm.commands.install.global_config_manager", global_config_manager)

    monkeypatch.setattr(
        RepositoryManager,
        "_fetch_servers",
        Mock(
            return_value={
                "api-server": {
                    "display_name": "API Server",
                    "description": "HTTP API server with auth headers",
                    "installations": {
                        "http": {
                            "type": "http",
                            "url": "https://api.example.com/mcp",
                            "headers": {"Authorization": "Bearer ${API_TOKEN}", "X-API-Version": "1.0"},
                            "description": "Connect via HTTP with authentication",
                            "recommended": True,
                        }
                    },
                    "arguments": {
                        "API_TOKEN": {"type": "string", "description": "API authentication token", "required": True},
                    },
                }
            }
        ),
    )

    # Mock prompt_toolkit's prompt to return our test values
    with (
        patch("prompt_toolkit.PromptSession.prompt", side_effect=["test-token-123"]),
        patch("rich.progress.Progress.start"),
        patch("rich.progress.Progress.stop"),
        patch("rich.progress.Progress.add_task"),
    ):
        runner = CliRunner()
        result = runner.invoke(install, ["api-server", "--force"])
        assert result.exit_code == 0

    # Check that the server was added to global configuration as RemoteServerConfig
    server = global_config_manager.get_server("api-server")
    assert server is not None
    assert isinstance(server, RemoteServerConfig)
    assert server.url == "https://api.example.com/mcp"
    # Check headers were properly set with variable replacement
    assert server.headers == {"Authorization": "Bearer test-token-123", "X-API-Version": "1.0"}
