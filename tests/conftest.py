"""
Pytest configuration for MCPM tests
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add the src directory to the path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcpm.clients.client_registry import ClientRegistry
from mcpm.clients.managers.claude_desktop import ClaudeDesktopManager
from mcpm.clients.managers.windsurf import WindsurfManager
from mcpm.utils.config import ConfigManager


@pytest.fixture
def temp_config_file():
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
def config_manager(monkeypatch):
    """Create a ClientConfigManager with a temp config for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_config_path = os.path.join(temp_dir, "config.json")
        # Create ConfigManager with the temp path

        _original_init = ConfigManager.__init__

        def _mock_init(self, config_path=tmp_config_path):
            _original_init(self, config_path)
            self.config_path = tmp_config_path

        monkeypatch.setattr(ConfigManager, "__init__", _mock_init)

        config_mgr = ConfigManager()
        # Create ClientConfigManager that will use this ConfigManager internally
        from mcpm.clients.client_config import ClientConfigManager

        client_mgr = ClientConfigManager()
        # Override its internal config_manager with our temp one
        client_mgr.config_manager = config_mgr
        yield client_mgr


@pytest.fixture
def windsurf_manager(temp_config_file, monkeypatch, config_manager):
    """Create a WindsurfManager instance using the temp config file"""
    windsurf_manager = WindsurfManager(config_path=temp_config_file)
    monkeypatch.setattr(ClientRegistry, "get_active_client_manager", Mock(return_value=windsurf_manager))
    monkeypatch.setattr(ClientRegistry, "get_client_manager", Mock(return_value=windsurf_manager))
    monkeypatch.setattr(ClientRegistry, "get_active_target", Mock(return_value="@windsurf"))
    return windsurf_manager


@pytest.fixture
def empty_windsurf_manager(empty_config_file):
    """Create a WindsurfManager instance with an empty config"""
    return WindsurfManager(config_path=empty_config_file)


@pytest.fixture
def claude_desktop_manager(temp_config_file):
    """Create a ClaudeDesktopManager instance with the temp config"""
    return ClaudeDesktopManager(config_path=temp_config_file)
