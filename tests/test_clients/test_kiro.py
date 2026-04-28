"""Tests for the Kiro client manager."""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from mcpm.clients.managers.kiro import KiroManager
from mcpm.core.schema import STDIOServerConfig


@pytest.fixture
def temp_json_config():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump({"mcpServers": {}}, f)
        temp_path = f.name

    yield temp_path
    os.unlink(temp_path)


@pytest.fixture
def kiro_manager(temp_json_config):
    return KiroManager(config_path_override=temp_json_config)


def test_default_config_path():
    """Test that the default config path is ~/.kiro/settings/mcp.json"""
    with patch.dict(os.environ, {"HOME": "/home/user"}, clear=False):
        manager = KiroManager()
        assert manager.config_path.endswith(".kiro/settings/mcp.json")


def test_config_path_override(temp_json_config):
    """Test that config_path_override takes precedence over the default path"""
    manager = KiroManager(config_path_override=temp_json_config)
    assert manager.config_path == temp_json_config


def test_get_empty_config(kiro_manager):
    """Test that empty config returns the standard mcpServers shape"""
    empty = kiro_manager._get_empty_config()
    assert empty == {"mcpServers": {}}


def test_uses_standard_mcpServers_key():
    """Test that Kiro uses the standard 'mcpServers' key (no override)"""
    assert KiroManager.configure_key_name == "mcpServers"


def test_get_client_info(kiro_manager):
    info = kiro_manager.get_client_info()
    assert info["name"] == "Kiro"
    assert info["download_url"] == "https://kiro.dev"
    assert "kiro" in info["description"].lower()
    assert "config_file" in info


def test_is_client_installed_when_kiro_on_path(kiro_manager):
    """Test that is_client_installed returns True when kiro binary is on PATH"""
    with patch("mcpm.clients.managers.kiro.shutil.which", return_value="/usr/local/bin/kiro"):
        assert kiro_manager.is_client_installed() is True


def test_is_client_installed_when_kiro_missing(kiro_manager):
    """Test that is_client_installed returns False when kiro binary is missing"""
    with patch("mcpm.clients.managers.kiro.shutil.which", return_value=None):
        assert kiro_manager.is_client_installed() is False


def test_add_and_list_server(kiro_manager):
    """Test the add_server / list_servers / get_server lifecycle"""
    server_config = STDIOServerConfig(
        name="test-server",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-test"],
    )
    success = kiro_manager.add_server(server_config)
    assert success

    servers = kiro_manager.list_servers()
    assert "test-server" in servers

    server = kiro_manager.get_server("test-server")
    assert server is not None
    assert server.name == "test-server"


def test_remove_server(kiro_manager):
    """Test the remove_server lifecycle"""
    server_config = STDIOServerConfig(
        name="test-server",
        command="npx",
        args=[],
    )
    kiro_manager.add_server(server_config)
    assert kiro_manager.remove_server("test-server") is True
    assert kiro_manager.get_server("test-server") is None


def test_load_config_returns_empty_when_file_missing():
    """Test that _load_config returns empty config shape when file doesn't exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        missing_path = os.path.join(tmpdir, "nonexistent.json")
        manager = KiroManager(config_path_override=missing_path)
        config = manager._load_config()
        assert config == {"mcpServers": {}}
