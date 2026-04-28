"""
Test for OpenCode manager
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from mcpm.clients.managers.opencode import OpenCodeManager


def test_opencode_manager_initialization():
    """Test OpenCodeManager initialization with default and override paths."""
    manager = OpenCodeManager()
    assert manager.client_key == "opencode"
    assert manager.display_name == "OpenCode"
    assert manager.download_url == "https://github.com/sst/opencode"
    assert manager.config_path == str(Path.home() / ".config" / "opencode" / "opencode.json")

    custom_path = "/tmp/custom_opencode.json"
    manager = OpenCodeManager(config_path_override=custom_path)
    assert manager.config_path == custom_path


def test_opencode_manager_uses_mcp_key_not_mcpservers():
    """Test that OpenCode uses the `mcp` key (not `mcpServers`).

    This is the OpenCode-specific configuration shape — the JSON file
    has a top-level `mcp` object instead of the `mcpServers` standard
    used by Claude Code, Cursor, Cline, etc.
    """
    manager = OpenCodeManager()
    assert manager.configure_key_name == "mcp"


def test_opencode_manager_get_empty_config():
    """Test OpenCodeManager _get_empty_config method returns the right shape."""
    manager = OpenCodeManager()
    config = manager._get_empty_config()
    assert "mcp" in config
    assert config["mcp"] == {}
    # Sanity: no mcpServers key (the standard one).
    assert "mcpServers" not in config


def test_opencode_manager_is_client_installed_true():
    """Test is_client_installed returns True when `opencode` binary is on PATH."""
    manager = OpenCodeManager()
    with patch("shutil.which", return_value="/usr/local/bin/opencode") as mock_which:
        assert manager.is_client_installed() is True
        mock_which.assert_called_with("opencode")


def test_opencode_manager_is_client_installed_false():
    """Test is_client_installed returns False when `opencode` is not on PATH."""
    manager = OpenCodeManager()
    with patch("shutil.which", return_value=None) as mock_which:
        assert manager.is_client_installed() is False
        mock_which.assert_called_with("opencode")


def test_opencode_manager_is_client_installed_windows():
    """Test that is_client_installed handles Windows PATHEXT via shutil.which."""
    manager = OpenCodeManager()
    # shutil.which() handles Windows PATHEXT automatically, so the manager
    # always searches for "opencode" (no .exe / .cmd suffix). This keeps
    # the manager OS-agnostic and matches the convention used by
    # CodexCliManager, QwenCliManager, etc.
    with patch("shutil.which", return_value="C:\\Users\\user\\AppData\\Roaming\\npm\\opencode.cmd") as mock_which:
        assert manager.is_client_installed() is True
        mock_which.assert_called_with("opencode")


def test_opencode_manager_get_client_info():
    """Test OpenCodeManager get_client_info method returns expected metadata."""
    manager = OpenCodeManager()
    info = manager.get_client_info()
    assert info["name"] == "OpenCode"
    assert info["download_url"] == "https://github.com/sst/opencode"
    assert info["config_file"] == str(Path.home() / ".config" / "opencode" / "opencode.json")
    assert "Open-source AI coding agent" in info["description"]


def test_opencode_manager_loads_existing_mcp_section():
    """Test that loading an existing config preserves the `mcp` section content."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
        json.dump(
            {
                "mcp": {
                    "memory": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-memory"],
                    }
                }
            },
            f,
        )
        temp_path = f.name

    try:
        manager = OpenCodeManager(config_path_override=temp_path)
        config = manager._load_config()
        assert "mcp" in config
        assert "memory" in config["mcp"]
        assert config["mcp"]["memory"]["command"] == "npx"
    finally:
        os.unlink(temp_path)


def test_opencode_manager_creates_empty_mcp_section_for_missing_file():
    """Test that loading a nonexistent file returns an empty `mcp` section."""
    nonexistent_path = "/tmp/nonexistent-opencode-config-test.json"
    manager = OpenCodeManager(config_path_override=nonexistent_path)
    config = manager._load_config()
    assert "mcp" in config
    assert config["mcp"] == {}


def test_opencode_manager_adds_server_under_mcp_key():
    """Test that adding a server writes it under the `mcp` key (not `mcpServers`)."""
    from mcpm.core.schema import STDIOServerConfig

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w") as f:
        json.dump({"mcp": {}}, f)
        temp_path = f.name

    try:
        manager = OpenCodeManager(config_path_override=temp_path)
        server_config = STDIOServerConfig(name="test-server", command="echo", args=["hello"])
        success = manager.add_server(server_config)
        assert success is True

        # Verify the server was written under `mcp`, not `mcpServers`.
        with open(temp_path) as f:
            saved = json.load(f)
        assert "mcp" in saved
        assert "test-server" in saved["mcp"]
        assert saved["mcp"]["test-server"]["command"] == "echo"
        assert "mcpServers" not in saved
    finally:
        os.unlink(temp_path)
