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
                        ]
                    }
                }
            }
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
    def config_manager(self):
        """Create a ConfigManager with a temp config for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = os.path.join(temp_dir, 'config.json')
            manager = ConfigManager(config_path=config_path)
            yield manager
    
    def test_get_servers(self, windsurf_manager):
        """Test retrieving servers from Windsurf config"""
        servers = windsurf_manager.get_servers()
        assert "test-server" in servers
        assert servers["test-server"]["command"] == "npx"
    
    def test_get_server(self, windsurf_manager):
        """Test retrieving a specific server from Windsurf config"""
        server = windsurf_manager.get_server("test-server")
        assert server is not None
        assert server["command"] == "npx"
        
        # Test non-existent server
        assert windsurf_manager.get_server("non-existent") is None
    
    def test_add_server(self, windsurf_manager):
        """Test adding a server to Windsurf config"""
        new_server = {
            "command": "npx",
            "args": [
                "-y",
                "@modelcontextprotocol/server-google-maps"
            ],
            "env": {
                "GOOGLE_MAPS_API_KEY": "test-key"
            }
        }
        
        success = windsurf_manager.add_server("google-maps", new_server)
        assert success
        
        # Verify server was added
        server = windsurf_manager.get_server("google-maps")
        assert server is not None
        assert server["command"] == "npx"
        assert "GOOGLE_MAPS_API_KEY" in server["env"]
    
    def test_remove_server(self, windsurf_manager):
        """Test removing a server from Windsurf config"""
        # First make sure server exists
        assert windsurf_manager.get_server("test-server") is not None
        
        # Remove the server
        success = windsurf_manager.remove_server("test-server")
        assert success
        
        # Verify it was removed
        assert windsurf_manager.get_server("test-server") is None
    
    def test_is_windsurf_installed(self, windsurf_manager):
        """Test checking if Windsurf is installed"""
        with patch('os.path.isdir', return_value=True):
            assert windsurf_manager.is_windsurf_installed()
        
        with patch('os.path.isdir', return_value=False):
            assert not windsurf_manager.is_windsurf_installed()
            
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
        config_manager.register_server("test-server", {"command": "npx"})
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
