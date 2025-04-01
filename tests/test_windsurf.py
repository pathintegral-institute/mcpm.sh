"""
Tests for Base Client Manager functionality through Windsurf implementation

This file tests the common functionality provided by BaseClientManager
using the WindsurfManager as a concrete implementation.
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from mcpm.clients.windsurf import WindsurfManager
from mcpm.utils.config import ConfigManager
from mcpm.utils.server_config import ServerConfig


class TestBaseClientManagerViaWindsurf:
    """Test BaseClientManager functionality via WindsurfManager implementation"""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary Windsurf config file for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            # Create a basic config with a test server
            config = {
                "mcpServers": {
                    "test-server": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-test"],
                        "version": "1.0.0",
                        "path": "/path/to/server",
                        "display_name": "Test Server",
                    }
                }
            }
            f.write(json.dumps(config).encode("utf-8"))
            temp_path = f.name

        yield temp_path
        # Clean up
        os.unlink(temp_path)

    @pytest.fixture
    def empty_config_file(self):
        """Create an empty temporary Windsurf config file for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            # Create an empty config
            config = {}
            f.write(json.dumps(config).encode("utf-8"))
            temp_path = f.name

        yield temp_path
        # Clean up
        os.unlink(temp_path)

    @pytest.fixture
    def windsurf_manager(self, temp_config_file):
        """Create a WindsurfManager instance using the temp config file"""
        return WindsurfManager(config_path=temp_config_file)

    @pytest.fixture
    def empty_windsurf_manager(self, empty_config_file):
        """Create a WindsurfManager instance with an empty config"""
        return WindsurfManager(config_path=empty_config_file)

    @pytest.fixture
    def sample_server_config(self):
        """Create a sample ServerConfig for testing"""
        return ServerConfig(
            name="sample-server",
            display_name="Sample Server",
            description="A sample server for testing",
            command="npx",
            args=["-y", "@modelcontextprotocol/sample-server"],
            env_vars={"API_KEY": "sample-key"},
            installation="default:npm",
        )

    @pytest.fixture
    def config_manager(self):
        """Create a ClientConfigManager with a temp config for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, "config.json")
            # Create ConfigManager with the temp path
            config_mgr = ConfigManager(config_path=config_path)
            # Create ClientConfigManager that will use this ConfigManager internally
            from mcpm.clients.client_config import ClientConfigManager

            client_mgr = ClientConfigManager()
            # Override its internal config_manager with our temp one
            client_mgr.config_manager = config_mgr
            yield client_mgr

    def test_list_servers(self, windsurf_manager):
        """Test list_servers method from BaseClientManager"""
        # list_servers returns a list of server names
        servers = windsurf_manager.list_servers()
        assert "test-server" in servers

    def test_get_server(self, windsurf_manager):
        """Test get_server method from BaseClientManager"""
        server = windsurf_manager.get_server("test-server")
        assert server is not None
        # Should return a ServerConfig object
        assert server.command == "npx"

        # Test non-existent server
        assert windsurf_manager.get_server("non-existent") is None

    def test_add_server_with_dict(self, windsurf_manager):
        """Test add_server method with dictionary input"""
        new_server = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-google-maps"],
            "env": {"GOOGLE_MAPS_API_KEY": "test-key"},
            "installation": "default:npm",
        }

        success = windsurf_manager.add_server(new_server, name="google-maps")
        assert success

        # Verify server was added using base get_server method
        server = windsurf_manager.get_server("google-maps")
        assert server is not None
        assert server.command == "npx"
        assert "GOOGLE_MAPS_API_KEY" in server.env_vars

    def test_add_server_to_empty_config(self, empty_windsurf_manager):
        """Test BaseClientManager creates mcpServers if it doesn't exist"""
        new_server = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-test"],
            "installation": "default:npm",
        }

        success = empty_windsurf_manager.add_server(new_server, name="test-server")
        assert success

        # Verify server was added via base get_server method
        server = empty_windsurf_manager.get_server("test-server")
        assert server is not None
        assert server.command == "npx"

    def test_add_server(self, windsurf_manager, sample_server_config):
        """Test add_server method from BaseClientManager"""
        success = windsurf_manager.add_server(sample_server_config)
        assert success

        # Verify server was added using base methods
        server = windsurf_manager.get_server("sample-server")
        assert server is not None
        assert "sample-server" in windsurf_manager.list_servers()

        # Verify essential fields are preserved by the base client conversion methods
        assert server.name == "sample-server"
        assert server.command == sample_server_config.command
        assert server.args == sample_server_config.args

    def test_convert_to_client_format(self, windsurf_manager, sample_server_config):
        """Test conversion from ServerConfig to Windsurf format"""
        windsurf_format = windsurf_manager.to_client_format(sample_server_config)

        # Check the format follows official Windsurf MCP format (command, args, env only)
        assert "command" in windsurf_format
        assert "args" in windsurf_format
        assert "env" in windsurf_format
        assert windsurf_format["command"] == sample_server_config.command
        assert windsurf_format["args"] == sample_server_config.args
        assert windsurf_format["env"]["API_KEY"] == "sample-key"

        # Verify we don't include metadata fields in the official format
        assert "name" not in windsurf_format
        assert "display_name" not in windsurf_format
        assert "version" not in windsurf_format
        assert "path" not in windsurf_format

    def test_remove_server(self, windsurf_manager):
        """Test remove_server method from BaseClientManager"""
        # First make sure server exists using base get_server method
        assert windsurf_manager.get_server("test-server") is not None

        # Remove the server using base remove_server method
        success = windsurf_manager.remove_server("test-server")
        assert success

        # Verify it was removed using base get_server method
        assert windsurf_manager.get_server("test-server") is None

    def test_from_client_format(self, windsurf_manager):
        """Test the base class from_client_format method"""
        # Create a minimal client config with required fields
        client_config = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-test"],
            "env": {"TEST_KEY": "test-value"},
        }

        # Test the base class from_client_format method directly
        server_config = windsurf_manager.from_client_format("test-server", client_config)

        # Check base conversion preserves essential fields
        assert isinstance(server_config, ServerConfig)
        assert server_config.name == "test-server"
        assert server_config.command == "npx"
        assert server_config.args == ["-y", "@modelcontextprotocol/server-test"]
        assert server_config.env_vars["TEST_KEY"] == "test-value"

    def test_get_all_servers_as_configs(self, windsurf_manager, sample_server_config):
        """Test getting all servers and converting them to ServerConfig objects"""
        # First add our sample server using base add_server method
        windsurf_manager.add_server(sample_server_config)

        # Get all servers and convert them to ServerConfig objects
        servers = windsurf_manager.get_servers()
        configs = [windsurf_manager.from_client_format(name, config) for name, config in servers.items()]

        # Should have at least 2 servers (test-server from fixture and sample-server we added)
        assert len(configs) >= 2

        # Find our sample server in the list
        sample_server = next((s for s in configs if s.name == "sample-server"), None)
        assert sample_server is not None
        # Verify essential execution fields are preserved
        assert sample_server.command == sample_server_config.command
        assert sample_server.args == sample_server_config.args

        # Find the test server in the list
        test_server = next((s for s in configs if s.name == "test-server"), None)
        assert test_server is not None

    def test_get_server_returns_server_config(self, windsurf_manager):
        """Test get_server method returns proper ServerConfig object"""
        config = windsurf_manager.get_server("test-server")

        assert config is not None
        assert isinstance(config, ServerConfig)
        assert config.name == "test-server"
        # When using base implementation, display_name defaults to server name
        # since we removed the client-specific implementation
        assert config.display_name == "test-server"

        # Test base class behavior with non-existent server
        assert windsurf_manager.get_server("non-existent") is None

    def test_is_client_installed(self, windsurf_manager):
        """Test checking if Windsurf is installed (now using is_client_installed)"""
        with patch("os.path.isdir", return_value=True):
            assert windsurf_manager.is_client_installed()

        with patch("os.path.isdir", return_value=False):
            assert not windsurf_manager.is_client_installed()

    def test_load_invalid_config(self):
        """Test loading an invalid config file"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
            # Write invalid JSON
            f.write(b"{invalid json")
            temp_path = f.name

        try:
            manager = WindsurfManager(config_path=temp_path)
            # Should get an empty config, not error
            config = manager._load_config()
            assert config == {"mcpServers": {}}
        finally:
            # Only try to delete if file exists
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_empty_config(self, empty_windsurf_manager):
        """Test BaseClientManager handling of empty config"""
        # Base class should return an empty list when no servers exist
        servers = empty_windsurf_manager.list_servers()
        assert servers == []

        # Verify we get an empty list, not None
        assert isinstance(servers, list)

    def test_distributed_architecture(self, config_manager, windsurf_manager, sample_server_config):
        """Test client manager in the distributed architecture"""
        # Make sure Windsurf is in supported clients
        supported_clients = config_manager.get_supported_clients()
        assert "windsurf" in supported_clients

        # Test setting Windsurf as active client
        success = config_manager.set_active_client("windsurf")
        assert success
        assert config_manager.get_active_client() == "windsurf"

        # In the distributed architecture, each client manages its own servers
        # using the base client manager functionality
        test_server_name = "config-test-server"
        server_info = {"command": "npx", "args": ["-p", "9000"]}
        windsurf_manager.add_server(server_info, name=test_server_name)

        # Check if server was added using list_servers
        server_list = windsurf_manager.list_servers()
        assert test_server_name in server_list

        # Test removing the server using base remove_server method
        windsurf_manager.remove_server(test_server_name)

        # Check if server was removed
        server_list = windsurf_manager.list_servers()
        assert test_server_name not in server_list
