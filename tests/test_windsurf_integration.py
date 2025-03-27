"""
Tests for Windsurf client integration with MCPM
"""

import os
import json
import pytest
import tempfile
from unittest.mock import patch

from mcpm.clients.windsurf import WindsurfManager
from mcpm.utils.config import ConfigManager
from mcpm.utils.server_config import ServerConfig


class TestWindsurfIntegration:
    """Test Windsurf client integration with MCPM"""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary Windsurf config file for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
            # Create a basic config with a test server
            config = {
                "mcpServers": {
                    "test-server": {
                        "command": "npx",
                        "args": [
                            "-y",
                            "@modelcontextprotocol/server-test"
                        ],
                        "version": "1.0.0",
                        "path": "/path/to/server",
                        "display_name": "Test Server"
                    }
                }
            }
            f.write(json.dumps(config).encode('utf-8'))
            temp_path = f.name
        
        yield temp_path
        # Clean up
        os.unlink(temp_path)

    @pytest.fixture
    def empty_config_file(self):
        """Create an empty temporary Windsurf config file for testing"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
            # Create an empty config
            config = {}
            f.write(json.dumps(config).encode('utf-8'))
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
            path="/path/to/sample/server",
            display_name="Sample Server",
            description="A sample server for testing",
            version="1.2.0",
            command="npx",
            args=["-y", "@modelcontextprotocol/sample-server"],
            env_vars={"API_KEY": "sample-key"}
        )
    
    @pytest.fixture
    def config_manager(self):
        """Create a ConfigManager with a temp config for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, 'config.json')
            manager = ConfigManager(config_path=config_path)
            yield manager
    
    def test_get_servers(self, windsurf_manager):
        """Test retrieving servers from Windsurf config"""
        # Changed to list_servers which returns a list of server names
        servers = windsurf_manager.list_servers()
        assert "test-server" in servers
    
    def test_get_server(self, windsurf_manager):
        """Test retrieving a specific server from Windsurf config"""
        server = windsurf_manager.get_server("test-server")
        assert server is not None
        # Now a ServerConfig object, not a dict
        assert server.command == "npx"
        
        # Test non-existent server
        assert windsurf_manager.get_server("non-existent") is None
    
    def test_add_server_config_raw(self, windsurf_manager):
        """Test adding a server to Windsurf config using the internal method"""
        new_server = {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-google-maps"
            ],
            "env": {
                "GOOGLE_MAPS_API_KEY": "test-key"
            },
            "path": "/path/to/google-maps"
        }
        
        success = windsurf_manager._add_server_config("google-maps", new_server)
        assert success
        
        # Verify server was added
        server = windsurf_manager.get_server("google-maps")
        assert server is not None
        assert server.command == "npx"
        assert "GOOGLE_MAPS_API_KEY" in server.env_vars
    
    def test_add_server_config_to_empty_config(self, empty_windsurf_manager):
        """Test adding a server to an empty config file using the internal method"""
        new_server = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-test"],
            "path": "/path/to/server"
        }
        
        success = empty_windsurf_manager._add_server_config("test-server", new_server)
        assert success
        
        # Verify server was added
        server = empty_windsurf_manager.get_server("test-server")
        assert server is not None
        assert server.command == "npx"
    
    def test_add_server(self, windsurf_manager, sample_server_config):
        """Test adding a ServerConfig object to Windsurf config"""
        success = windsurf_manager.add_server(sample_server_config)
        assert success
        
        # Verify server was added
        server = windsurf_manager.get_server("sample-server")
        assert server is not None
        assert "sample-server" in windsurf_manager.list_servers()
        
        # Since get_server now returns a ServerConfig, we can directly compare
        assert server is not None
        assert server.name == "sample-server"
        # Note: With the official Windsurf format, metadata fields aren't preserved
        # Only essential execution fields (command, args, env) are preserved
        assert server.command == sample_server_config.command
        assert server.args == sample_server_config.args
    
    def test_convert_to_client_format(self, windsurf_manager, sample_server_config):
        """Test conversion from ServerConfig to Windsurf format"""
        windsurf_format = windsurf_manager._convert_to_client_format(sample_server_config)
        
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
        """Test removing a server from Windsurf config"""
        # First make sure server exists
        assert windsurf_manager.get_server("test-server") is not None
        
        # Remove the server
        success = windsurf_manager.remove_server("test-server")
        assert success
        
        # Verify it was removed
        assert windsurf_manager.get_server("test-server") is None
    
    def test_convert_from_client_format(self, windsurf_manager):
        """Test conversion from Windsurf format to ServerConfig"""
        windsurf_config = {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-test"],
            "env": {"TEST_KEY": "test-value"},
            "path": "/path/to/server",
            "display_name": "test-convert",  # Updated to match the server name
            "version": "1.0.0"
        }
        
        server_config = windsurf_manager._convert_from_client_format("test-convert", windsurf_config)
        
        # Check conversion is correct
        assert isinstance(server_config, ServerConfig)
        assert server_config.name == "test-convert"
        assert server_config.display_name == "test-convert"
        assert server_config.command == "npx"
        assert server_config.args == ["-y", "@modelcontextprotocol/server-test"]
        assert server_config.env_vars["TEST_KEY"] == "test-value"
        assert server_config.path == "/path/to/server"
    
    def test_get_server_configs(self, windsurf_manager, sample_server_config):
        """Test retrieving all servers as ServerConfig objects"""
        # First add our sample server
        windsurf_manager.add_server(sample_server_config)
        
        configs = windsurf_manager.get_server_configs()
        
        # Should have at least 2 servers (test-server from fixture and sample-server we added)
        assert len(configs) >= 2
        
        # Find our sample server in the list
        sample_server = next((s for s in configs if s.name == "sample-server"), None)
        assert sample_server is not None
        # Verify essential execution fields are preserved, even if metadata isn't
        assert sample_server.command == sample_server_config.command
        assert sample_server.args == sample_server_config.args
        
        # Find the test server in the list
        test_server = next((s for s in configs if s.name == "test-server"), None)
        assert test_server is not None
    
    def test_get_server_config(self, windsurf_manager):
        """Test retrieving a specific server as a ServerConfig object"""
        # get_server now returns a ServerConfig, so get_server_config is redundant
        config = windsurf_manager.get_server("test-server")
        
        assert config is not None
        assert isinstance(config, ServerConfig)
        assert config.name == "test-server"
        # The display_name is coming from our test fixture where it's set to "Test Server"
        assert config.display_name == "Test Server"
        
        # Non-existent server should return None
        assert windsurf_manager.get_server("non-existent") is None
        
    def test_is_client_installed(self, windsurf_manager):
        """Test checking if Windsurf is installed (now using is_client_installed)"""
        with patch('os.path.isdir', return_value=True):
            assert windsurf_manager.is_client_installed()
        
        with patch('os.path.isdir', return_value=False):
            assert not windsurf_manager.is_client_installed()
    
    def test_load_invalid_config(self):
        """Test loading an invalid config file"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
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
        """Test handling empty config"""
        servers = empty_windsurf_manager.get_servers()
        assert servers == {}
        
        # Verify we get an empty dict, not None
        assert isinstance(servers, dict)
            
    def test_config_manager_integration(self, config_manager):
        """Test ConfigManager integration with Windsurf client"""
        # Make sure Windsurf is in supported clients
        supported_clients = config_manager.get_supported_clients()
        assert "windsurf" in supported_clients
        
        # Test setting Windsurf as active client
        success = config_manager.set_active_client("windsurf")
        assert success
        assert config_manager.get_active_client() == "windsurf"
        
        # Test server enabling/disabling for Windsurf
        config_manager.register_server("test-server", {"command": "npx", "path": "/path/to/server"})
        success = config_manager.enable_server_for_client("test-server", "windsurf")
        assert success
        
        # Check if server was enabled
        windsurf_servers = config_manager.get_client_servers("windsurf")
        assert "test-server" in windsurf_servers
        
        # Test disabling
        success = config_manager.disable_server_for_client("test-server", "windsurf")
        assert success
        
        # Check if server was disabled
        windsurf_servers = config_manager.get_client_servers("windsurf")
        assert "test-server" not in windsurf_servers
