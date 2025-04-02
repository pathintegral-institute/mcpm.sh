"""
Pytest configuration for MCPM tests
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add the src directory to the path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent))

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
def config_manager():
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


@pytest.fixture
def windsurf_manager(temp_config_file):
    """Create a WindsurfManager instance using the temp config file"""
    return WindsurfManager(config_path=temp_config_file)


@pytest.fixture
def empty_windsurf_manager(empty_config_file):
    """Create a WindsurfManager instance with an empty config"""
    return WindsurfManager(config_path=empty_config_file)
