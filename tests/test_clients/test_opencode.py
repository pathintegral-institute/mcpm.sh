"""
Tests for OpenCode manager
"""

import json
import os
from unittest.mock import patch

import pytest

from mcpm.clients.managers.opencode import OpenCodeManager
from mcpm.core.schema import RemoteServerConfig, STDIOServerConfig


@pytest.fixture
def tmp_config(tmp_path):
    """Return path to a temporary OpenCode config file."""
    return str(tmp_path / "opencode.json")


@pytest.fixture
def manager(tmp_config):
    """Create an OpenCodeManager with a temp config path."""
    return OpenCodeManager(config_path_override=tmp_config)


@pytest.fixture
def manager_with_config(tmp_path):
    """Create manager with a pre-populated config file."""
    cfg_path = str(tmp_path / "opencode.json")
    with open(cfg_path, "w") as f:
        json.dump(
            {
                "$schema": "https://opencode.ai/config.json",
                "model": "anthropic/claude-sonnet-4-5",
                "mcp": {
                    "existing-server": {
                        "type": "local",
                        "command": ["node", "server.js"],
                        "environment": {"TOKEN": "abc"},
                    }
                },
            },
            f,
        )
    return OpenCodeManager(config_path_override=cfg_path)


@pytest.fixture
def sample_stdio_server():
    return STDIOServerConfig(
        name="test-server",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-everything"],
        env={"API_KEY": "secret"},
    )


@pytest.fixture
def sample_remote_server():
    return RemoteServerConfig(
        name="remote-server",
        url="https://mcp.example.com/sse",
        headers={"Authorization": "Bearer token123"},
    )


# ------------------------------------------------------------------
# Initialization
# ------------------------------------------------------------------


def test_client_attributes():
    """Verify class-level client metadata."""
    manager = OpenCodeManager(config_path_override="/tmp/fake.json")
    assert manager.client_key == "opencode"
    assert manager.display_name == "OpenCode"
    assert manager.configure_key_name == "mcp"


def test_default_config_path():
    """Default config path points to XDG location."""
    manager = OpenCodeManager()
    assert manager.config_path == os.path.expanduser("~/.config/opencode/opencode.json")


def test_config_path_override():
    manager = OpenCodeManager(config_path_override="/custom/path.json")
    assert manager.config_path == "/custom/path.json"


def test_empty_config():
    manager = OpenCodeManager(config_path_override="/tmp/fake.json")
    config = manager._get_empty_config()
    assert config["$schema"] == "https://opencode.ai/config.json"
    assert config["mcp"] == {}


# ------------------------------------------------------------------
# Client detection
# ------------------------------------------------------------------


def test_is_client_installed_true():
    manager = OpenCodeManager(config_path_override="/tmp/fake.json")
    with patch("shutil.which", return_value="/usr/local/bin/opencode"):
        assert manager.is_client_installed() is True


def test_is_client_installed_false():
    manager = OpenCodeManager(config_path_override="/tmp/fake.json")
    with patch("shutil.which", return_value=None):
        assert manager.is_client_installed() is False


def test_get_client_info(manager):
    info = manager.get_client_info()
    assert info["name"] == "OpenCode"
    assert info["download_url"] == "https://opencode.ai"
    assert "config_file" in info


# ------------------------------------------------------------------
# to_client_format — local servers
# ------------------------------------------------------------------


def test_to_client_format_local(manager, sample_stdio_server):
    result = manager.to_client_format(sample_stdio_server)
    assert result["type"] == "local"
    assert result["command"] == ["npx", "-y", "@modelcontextprotocol/server-everything"]
    assert result["environment"]["API_KEY"] == "secret"
    # Must NOT use the old "env" key
    assert "env" not in result
    # Must NOT include "args" as a separate key
    assert "args" not in result


def test_to_client_format_local_no_args(manager):
    server = STDIOServerConfig(name="simple", command="node", args=[], env={})
    result = manager.to_client_format(server)
    assert result["type"] == "local"
    assert result["command"] == ["node"]
    assert "environment" not in result


def test_to_client_format_local_no_env(manager):
    server = STDIOServerConfig(name="no-env", command="npx", args=["-y", "pkg"], env={})
    result = manager.to_client_format(server)
    assert "environment" not in result


# ------------------------------------------------------------------
# to_client_format — remote servers
# ------------------------------------------------------------------


def test_to_client_format_remote(manager, sample_remote_server):
    result = manager.to_client_format(sample_remote_server)
    assert result["type"] == "remote"
    assert result["url"] == "https://mcp.example.com/sse"
    assert result["headers"]["Authorization"] == "Bearer token123"


def test_to_client_format_remote_no_headers(manager):
    server = RemoteServerConfig(name="bare", url="https://example.com/mcp", headers={})
    result = manager.to_client_format(server)
    assert result["type"] == "remote"
    assert result["url"] == "https://example.com/mcp"
    assert "headers" not in result


# ------------------------------------------------------------------
# from_client_format — local servers
# ------------------------------------------------------------------


def test_from_client_format_local():
    config = {
        "type": "local",
        "command": ["npx", "-y", "@modelcontextprotocol/server-everything"],
        "environment": {"API_KEY": "secret"},
    }
    server = OpenCodeManager.from_client_format("test", config)
    assert isinstance(server, STDIOServerConfig)
    assert server.name == "test"
    assert server.command == "npx"
    assert server.args == ["-y", "@modelcontextprotocol/server-everything"]
    assert server.env == {"API_KEY": "secret"}


def test_from_client_format_local_single_command():
    config = {"type": "local", "command": ["node"]}
    server = OpenCodeManager.from_client_format("simple", config)
    assert isinstance(server, STDIOServerConfig)
    assert server.command == "node"
    assert server.args == []


def test_from_client_format_local_empty_command():
    config = {"type": "local", "command": []}
    server = OpenCodeManager.from_client_format("empty", config)
    assert isinstance(server, STDIOServerConfig)
    assert server.command == ""
    assert server.args == []


def test_from_client_format_defaults_to_local():
    """Missing 'type' field defaults to local."""
    config = {"command": ["python", "-m", "my_server"]}
    server = OpenCodeManager.from_client_format("inferred", config)
    assert isinstance(server, STDIOServerConfig)
    assert server.command == "python"
    assert server.args == ["-m", "my_server"]


# ------------------------------------------------------------------
# from_client_format — remote servers
# ------------------------------------------------------------------


def test_from_client_format_remote():
    config = {
        "type": "remote",
        "url": "https://mcp.example.com/sse",
        "headers": {"Authorization": "Bearer abc"},
    }
    server = OpenCodeManager.from_client_format("remote-test", config)
    assert isinstance(server, RemoteServerConfig)
    assert server.name == "remote-test"
    assert server.url == "https://mcp.example.com/sse"
    assert server.headers["Authorization"] == "Bearer abc"


def test_from_client_format_remote_no_headers():
    config = {"type": "remote", "url": "https://example.com/mcp"}
    server = OpenCodeManager.from_client_format("bare-remote", config)
    assert isinstance(server, RemoteServerConfig)
    assert server.headers == {}


# ------------------------------------------------------------------
# CRUD operations
# ------------------------------------------------------------------


def test_add_and_get_server(manager, sample_stdio_server):
    assert manager.add_server(sample_stdio_server)
    retrieved = manager.get_server("test-server")
    assert retrieved is not None
    assert retrieved.command == "npx"
    assert retrieved.args == ["-y", "@modelcontextprotocol/server-everything"]


def test_add_server_writes_correct_json(manager, sample_stdio_server):
    manager.add_server(sample_stdio_server)
    with open(manager.config_path) as f:
        data = json.load(f)

    assert "mcp" in data
    entry = data["mcp"]["test-server"]
    assert entry["type"] == "local"
    assert entry["command"] == ["npx", "-y", "@modelcontextprotocol/server-everything"]
    assert entry["environment"]["API_KEY"] == "secret"
    assert "env" not in entry


def test_list_servers(manager):
    for name in ["alpha", "beta"]:
        manager.add_server(STDIOServerConfig(name=name, command="node", args=[], env={}))
    assert set(manager.list_servers()) == {"alpha", "beta"}


def test_remove_server(manager, sample_stdio_server):
    manager.add_server(sample_stdio_server)
    assert manager.remove_server("test-server")
    assert manager.list_servers() == []


def test_remove_nonexistent_server(manager):
    assert manager.remove_server("ghost") is False


def test_get_nonexistent_server(manager):
    assert manager.get_server("ghost") is None


# ------------------------------------------------------------------
# Roundtrip: add → get matches original
# ------------------------------------------------------------------


def test_roundtrip_local(manager, sample_stdio_server):
    manager.add_server(sample_stdio_server)
    retrieved = manager.get_server("test-server")
    assert isinstance(retrieved, STDIOServerConfig)
    assert retrieved.command == sample_stdio_server.command
    assert retrieved.args == sample_stdio_server.args


def test_roundtrip_remote(manager, sample_remote_server):
    manager.add_server(sample_remote_server)
    retrieved = manager.get_server("remote-server")
    assert isinstance(retrieved, RemoteServerConfig)
    assert retrieved.url == sample_remote_server.url
    assert retrieved.headers == sample_remote_server.headers


# ------------------------------------------------------------------
# Preserves existing config keys
# ------------------------------------------------------------------


def test_preserves_existing_keys(manager_with_config):
    mgr = manager_with_config
    server = STDIOServerConfig(name="new-server", command="node", args=[], env={})
    mgr.add_server(server)

    with open(mgr.config_path) as f:
        data = json.load(f)

    # Non-mcp keys preserved
    assert data["model"] == "anthropic/claude-sonnet-4-5"
    assert data["$schema"] == "https://opencode.ai/config.json"
    # Both servers present
    assert "existing-server" in data["mcp"]
    assert "new-server" in data["mcp"]


def test_preserves_existing_server_on_add(manager_with_config):
    mgr = manager_with_config
    server = STDIOServerConfig(name="second", command="python", args=["-m", "srv"], env={})
    mgr.add_server(server)

    existing = mgr.get_server("existing-server")
    assert existing is not None
    assert existing.command == "node"


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------


def test_load_invalid_json(tmp_path):
    cfg_path = str(tmp_path / "opencode.json")
    with open(cfg_path, "w") as f:
        f.write("{invalid json")

    mgr = OpenCodeManager(config_path_override=cfg_path)
    # Should handle gracefully, not crash
    servers = mgr.list_servers()
    assert servers == []


def test_load_missing_file(tmp_path):
    cfg_path = str(tmp_path / "nonexistent.json")
    mgr = OpenCodeManager(config_path_override=cfg_path)
    servers = mgr.list_servers()
    assert servers == []


def test_load_jsonc_with_comments(tmp_path):
    """OpenCode supports JSONC — comments must not break parsing."""
    cfg_path = str(tmp_path / "opencode.json")
    with open(cfg_path, "w") as f:
        f.write(
            """{
  "$schema": "https://opencode.ai/config.json",
  // This is a comment
  "model": "anthropic/claude-sonnet-4-5",
  "mcp": {
    "test-server": {
      "type": "local",
      // Server command
      "command": ["npx", "-y", "my-server"],
    }
  },
}"""
        )

    mgr = OpenCodeManager(config_path_override=cfg_path)
    servers = mgr.list_servers()
    assert "test-server" in servers
    server = mgr.get_server("test-server")
    assert server.command == "npx"
    assert server.args == ["-y", "my-server"]


def test_jsonc_preserves_urls_with_slashes(tmp_path):
    """Comments inside strings (e.g. URLs with ://) must not be stripped."""
    cfg_path = str(tmp_path / "opencode.json")
    with open(cfg_path, "w") as f:
        f.write(
            """{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "remote": {
      "type": "remote",
      "url": "https://mcp.example.com/sse"
    }
  }
}"""
        )

    mgr = OpenCodeManager(config_path_override=cfg_path)
    server = mgr.get_server("remote")
    assert server.url == "https://mcp.example.com/sse"


def test_from_client_format_string_command():
    """Handle command as a plain string (not array)."""
    config = {"type": "local", "command": "node"}
    server = OpenCodeManager.from_client_format("str-cmd", config)
    assert isinstance(server, STDIOServerConfig)
    assert server.command == "node"
    assert server.args == []


def test_from_client_format_string_command_with_args():
    """String command with separate args list (non-standard but defensive)."""
    config = {"type": "local", "command": "node", "args": ["server.js", "--port=3000"]}
    server = OpenCodeManager.from_client_format("str-with-args", config)
    assert isinstance(server, STDIOServerConfig)
    assert server.command == "node"
    assert server.args == ["server.js", "--port=3000"]


def test_jsonc_inline_comments_and_string_edge_cases(tmp_path):
    """Inline comments and strings containing ,} or ,] must parse correctly."""
    cfg_path = str(tmp_path / "opencode.json")
    with open(cfg_path, "w") as f:
        f.write(
            """{
  "$schema": "https://opencode.ai/config.json",
  "model": "anthropic/claude-sonnet-4-5", // inline comment
  "description": "contains ,} and ,] inside string",
  "mcp": {
    "test-server": {
      "type": "local",
      "command": ["node", "server.js"], // another inline comment
    }
  },
}"""
        )

    mgr = OpenCodeManager(config_path_override=cfg_path)
    server = mgr.get_server("test-server")
    assert server.command == "node"
    assert server.args == ["server.js"]

    config = mgr._load_config()
    assert config["description"] == "contains ,} and ,] inside string"


def test_from_client_format_malformed_args():
    """Non-list args should be coerced to a list."""
    config = {"type": "local", "command": "node", "args": "server.js"}
    server = OpenCodeManager.from_client_format("bad-args", config)
    assert isinstance(server, STDIOServerConfig)
    assert server.command == "node"
    assert server.args == ["server.js"]


def test_from_client_format_malformed_env():
    """Non-dict environment should fall back to empty dict."""
    config = {"type": "local", "command": ["node"], "environment": ["not", "a", "dict"]}
    server = OpenCodeManager.from_client_format("bad-env", config)
    assert isinstance(server, STDIOServerConfig)
    assert server.env == {}


# ------------------------------------------------------------------
# enabled field
# ------------------------------------------------------------------


def test_to_client_format_disabled(manager):
    server = STDIOServerConfig(name="disabled-server", command="npx", args=["-y", "pkg"], enabled=False)
    result = manager.to_client_format(server)
    assert result["enabled"] is False


def test_to_client_format_enabled_none_not_written(manager):
    server = STDIOServerConfig(name="default-server", command="npx", args=["-y", "pkg"])
    result = manager.to_client_format(server)
    assert "enabled" not in result


def test_roundtrip_disabled(manager):
    server = STDIOServerConfig(name="disabled-server", command="npx", args=["-y", "pkg"], enabled=False)
    manager.add_server(server)
    retrieved = manager.get_server("disabled-server")
    assert isinstance(retrieved, STDIOServerConfig)
    assert retrieved.enabled is False
