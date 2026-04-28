"""Tests for the Sourcegraph Amp client manager."""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from mcpm.clients.managers.amp import AmpManager
from mcpm.core.schema import STDIOServerConfig


@pytest.fixture
def temp_json_config():
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump({"amp.mcpServers": {}}, f)
        temp_path = f.name

    yield temp_path
    os.unlink(temp_path)


@pytest.fixture
def amp_manager(temp_json_config):
    return AmpManager(config_path_override=temp_json_config)


def test_default_config_path():
    """Test that the default config path is ~/.config/amp/settings.json"""
    manager = AmpManager()
    assert manager.config_path.endswith(".config/amp/settings.json")


def test_config_path_override(temp_json_config):
    """Test that config_path_override takes precedence over the default path"""
    manager = AmpManager(config_path_override=temp_json_config)
    assert manager.config_path == temp_json_config


def test_uses_dotted_amp_mcpServers_key():
    """Test that Amp uses the literal `amp.mcpServers` key (not nested)"""
    assert AmpManager.configure_key_name == "amp.mcpServers"


def test_get_empty_config(amp_manager):
    """Test that empty config returns the dotted-key shape"""
    empty = amp_manager._get_empty_config()
    assert empty == {"amp.mcpServers": {}}


def test_get_client_info(amp_manager):
    info = amp_manager.get_client_info()
    assert info["name"] == "Sourcegraph Amp"
    assert info["download_url"] == "https://ampcode.com"
    assert "amp" in info["description"].lower()
    assert "config_file" in info


def test_is_client_installed_when_amp_on_path(amp_manager):
    """Test that is_client_installed returns True when amp binary is on PATH"""
    with patch("mcpm.clients.managers.amp.shutil.which", return_value="/usr/local/bin/amp"):
        assert amp_manager.is_client_installed() is True


def test_is_client_installed_when_amp_missing(amp_manager):
    """Test that is_client_installed returns False when amp binary is missing"""
    with patch("mcpm.clients.managers.amp.shutil.which", return_value=None):
        assert amp_manager.is_client_installed() is False


def test_add_and_list_server(amp_manager):
    """Test the add_server / list_servers / get_server lifecycle"""
    server_config = STDIOServerConfig(
        name="test-server",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-test"],
    )
    success = amp_manager.add_server(server_config)
    assert success

    servers = amp_manager.list_servers()
    assert "test-server" in servers

    server = amp_manager.get_server("test-server")
    assert server is not None
    assert server.name == "test-server"


def test_remove_server(amp_manager):
    """Test the remove_server lifecycle"""
    server_config = STDIOServerConfig(
        name="test-server",
        command="npx",
        args=[],
    )
    amp_manager.add_server(server_config)
    assert amp_manager.remove_server("test-server") is True
    assert amp_manager.get_server("test-server") is None


def test_load_config_returns_empty_when_file_missing():
    """Test that _load_config returns empty config shape when file doesn't exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        missing_path = os.path.join(tmpdir, "nonexistent.json")
        manager = AmpManager(config_path_override=missing_path)
        config = manager._load_config()
        assert config == {"amp.mcpServers": {}}


def test_preserves_other_keys_when_adding_server():
    """Test that adding a server preserves unrelated top-level keys
    (e.g. amp.theme, amp.modelOverrides) so we don't clobber Amp settings."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        json.dump({"amp.mcpServers": {}, "amp.theme": "dark", "amp.foo": "bar"}, f)
        temp_path = f.name

    try:
        manager = AmpManager(config_path_override=temp_path)
        server_config = STDIOServerConfig(
            name="test-server",
            command="npx",
            args=[],
        )
        manager.add_server(server_config)
        with open(temp_path) as f:
            config = json.load(f)
        # amp.mcpServers got the new server
        assert "test-server" in config["amp.mcpServers"]
        # Unrelated keys survived
        assert config["amp.theme"] == "dark"
        assert config["amp.foo"] == "bar"
    finally:
        os.unlink(temp_path)
