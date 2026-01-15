"""
Tests for VSCode Manager functionality

This file tests the VSCode-specific MCP configuration management,
including the new mcp.json structure with servers at root level.
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from mcpm.clients.managers.vscode import VSCodeManager
from mcpm.core.schema import STDIOServerConfig


class TestVSCodeManager:
    """Test VSCodeManager implementation"""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary VSCode config file for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            # Create a config with the new mcp.json structure
            config = {
                "servers": {
                    "test-server": {
                        "type": "stdio",
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-test"],
                    }
                },
                "inputs": [],
            }
            f.write(json.dumps(config).encode("utf-8"))
            temp_path = f.name

        yield temp_path
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def empty_config_file(self):
        """Create an empty temporary VSCode config file for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            # Create an empty config
            config = {}
            f.write(json.dumps(config).encode("utf-8"))
            temp_path = f.name

        yield temp_path
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    @pytest.fixture
    def vscode_manager(self, temp_config_file):
        """Create a VSCodeManager instance using the temp config file"""
        return VSCodeManager(config_path_override=temp_config_file)

    @pytest.fixture
    def empty_vscode_manager(self, empty_config_file):
        """Create a VSCodeManager instance with an empty config"""
        return VSCodeManager(config_path_override=empty_config_file)

    @pytest.fixture
    def sample_server_config(self):
        """Create a sample ServerConfig for testing"""
        return STDIOServerConfig(
            name="sample-server",
            command="npx",
            args=["-y", "@modelcontextprotocol/sample-server"],
            env={"API_KEY": "sample-key"},
        )

    def test_config_path_macos(self):
        """Test that config path is correct for macOS"""
        with patch("platform.system", return_value="Darwin"):
            manager = VSCodeManager()
            assert manager.config_path == os.path.expanduser("~/Library/Application Support/Code/User/mcp.json")

    def test_config_path_windows(self):
        """Test that config path is correct for Windows"""
        with patch("platform.system", return_value="Windows"):
            with patch.dict(os.environ, {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}):
                manager = VSCodeManager()
                # Normalize path for comparison as os.path.join behavior differs on different platforms
                expected = os.path.join("C:\\Users\\Test\\AppData\\Roaming", "Code", "User", "mcp.json")
                assert manager.config_path == expected

    def test_config_path_linux(self):
        """Test that config path is correct for Linux"""
        with patch("platform.system", return_value="Linux"):
            manager = VSCodeManager()
            assert manager.config_path == os.path.expanduser("~/.config/Code/User/mcp.json")

    def test_load_config_structure(self, vscode_manager):
        """Test that _load_config returns the correct structure"""
        config = vscode_manager._load_config()

        # Should have servers at root level
        assert "servers" in config
        assert isinstance(config["servers"], dict)

        # Should have inputs array
        assert "inputs" in config
        assert isinstance(config["inputs"], list)

        # Should NOT have MCP wrapper
        assert "mcp" not in config

    def test_load_config_preserves_servers(self, vscode_manager):
        """Test that _load_config preserves existing servers"""
        config = vscode_manager._load_config()

        # Should have the test server
        assert "test-server" in config["servers"]
        assert config["servers"]["test-server"]["command"] == "npx"

    def test_save_config_structure(self, vscode_manager):
        """Test that _save_config saves with correct structure"""
        new_config = {
            "servers": {
                "new-server": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["server.js"],
                }
            },
            "inputs": [],
        }

        success = vscode_manager._save_config(new_config)
        assert success

        # Read back and verify structure
        with open(vscode_manager.config_path, "r") as f:
            saved_config = json.load(f)

        # Should have servers at root level
        assert "servers" in saved_config
        assert "new-server" in saved_config["servers"]

        # Should have inputs array
        assert "inputs" in saved_config

        # Should NOT have MCP wrapper
        assert "mcp" not in saved_config

    def test_save_config_preserves_inputs(self, vscode_manager):
        """Test that _save_config preserves inputs array"""
        new_config = {
            "servers": {
                "new-server": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["server.js"],
                }
            },
            "inputs": [{"id": "test-input", "type": "text"}],
        }

        success = vscode_manager._save_config(new_config)
        assert success

        # Read back and verify inputs preserved
        with open(vscode_manager.config_path, "r") as f:
            saved_config = json.load(f)

        assert "inputs" in saved_config
        assert len(saved_config["inputs"]) == 1
        assert saved_config["inputs"][0]["id"] == "test-input"

    def test_save_config_adds_inputs_if_missing(self, vscode_manager):
        """Test that _save_config adds inputs array if not present"""
        new_config = {
            "servers": {
                "new-server": {
                    "type": "stdio",
                    "command": "node",
                    "args": ["server.js"],
                }
            }
        }

        success = vscode_manager._save_config(new_config)
        assert success

        # Read back and verify inputs was added
        with open(vscode_manager.config_path, "r") as f:
            saved_config = json.load(f)

        assert "inputs" in saved_config
        assert isinstance(saved_config["inputs"], list)
        assert len(saved_config["inputs"]) == 0

    def test_list_servers(self, vscode_manager):
        """Test list_servers method"""
        servers = vscode_manager.list_servers()
        assert "test-server" in servers

    def test_get_server(self, vscode_manager):
        """Test get_server method"""
        server = vscode_manager.get_server("test-server")
        assert server is not None
        assert server.command == "npx"

        # Test non-existent server
        assert vscode_manager.get_server("non-existent") is None

    def test_add_server(self, vscode_manager, sample_server_config):
        """Test add_server method"""
        success = vscode_manager.add_server(sample_server_config)
        assert success

        # Verify server was added
        server = vscode_manager.get_server("sample-server")
        assert server is not None
        assert "sample-server" in vscode_manager.list_servers()

        # Verify essential fields are preserved
        assert server.name == "sample-server"
        assert server.command == sample_server_config.command
        assert server.args == sample_server_config.args

    def test_to_client_format(self, vscode_manager, sample_server_config):
        """Test conversion from ServerConfig to VSCode format"""
        vscode_format = vscode_manager.to_client_format(sample_server_config)

        # VSCode expects type, command, args, and env
        assert "type" in vscode_format
        assert vscode_format["type"] == "stdio"
        assert "command" in vscode_format
        assert "args" in vscode_format
        assert "env" in vscode_format
        assert vscode_format["command"] == sample_server_config.command
        assert vscode_format["args"] == sample_server_config.args
        assert vscode_format["env"]["API_KEY"] == "sample-key"

        # Verify we don't include metadata fields
        assert "name" not in vscode_format
        assert "display_name" not in vscode_format
        assert "version" not in vscode_format

    def test_remove_server(self, vscode_manager):
        """Test remove_server method"""
        # First make sure server exists
        assert vscode_manager.get_server("test-server") is not None

        # Remove the server
        success = vscode_manager.remove_server("test-server")
        assert success

        # Verify it was removed
        assert vscode_manager.get_server("test-server") is None

    def test_from_client_format(self, vscode_manager):
        """Test conversion from VSCode format to ServerConfig"""
        client_config = {
            "type": "stdio",
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-test"],
            "env": {"TEST_KEY": "test-value"},
        }

        server_config = vscode_manager.from_client_format("test-server", client_config)

        assert isinstance(server_config, STDIOServerConfig)
        assert server_config.name == "test-server"
        assert server_config.command == "npx"
        assert server_config.args == ["-y", "@modelcontextprotocol/server-test"]
        assert server_config.env["TEST_KEY"] == "test-value"

    def test_empty_config(self, empty_vscode_manager):
        """Test handling of empty config"""
        servers = empty_vscode_manager.list_servers()
        assert servers == []
        assert isinstance(servers, list)

    def test_load_invalid_config(self):
        """Test loading an invalid config file"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            # Write invalid JSON
            f.write(b"{invalid json")
            temp_path = f.name

        try:
            manager = VSCodeManager(config_path_override=temp_path)
            # Should get an empty config, not error
            config = manager._load_config()
            assert "servers" in config
            assert config["servers"] == {}
            assert "inputs" in config
            assert config["inputs"] == []
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_load_config_without_file(self):
        """Test loading config when file doesn't exist"""
        nonexistent_path = os.path.join(tempfile.gettempdir(), "nonexistent-vscode-config.json")
        manager = VSCodeManager(config_path_override=nonexistent_path)
        config = manager._load_config()

        # Should return empty config structure
        assert "servers" in config
        assert config["servers"] == {}
        assert "inputs" in config
        assert config["inputs"] == []

    def test_config_migration_compatibility(self, vscode_manager):
        """Test that config works with the expected VS Code format"""
        # Add a server and verify it's saved in the correct format
        server_config = STDIOServerConfig(
            name="mcpm_profile_work",
            command="mcpm",
            args=["profile", "run", "work"],
        )

        vscode_manager.add_server(server_config)

        # Read the file directly to verify structure
        with open(vscode_manager.config_path, "r") as f:
            saved_config = json.load(f)

        # Verify expected structure from problem statement
        assert "servers" in saved_config
        assert "mcpm_profile_work" in saved_config["servers"]
        assert saved_config["servers"]["mcpm_profile_work"]["type"] == "stdio"
        assert saved_config["servers"]["mcpm_profile_work"]["command"] == "mcpm"
        assert saved_config["servers"]["mcpm_profile_work"]["args"] == ["profile", "run", "work"]
        assert "inputs" in saved_config
        assert isinstance(saved_config["inputs"], list)
