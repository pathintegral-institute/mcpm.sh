"""
Tests for the profile module
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.schemas.server_config import RemoteServerConfig, STDIOServerConfig


@pytest.fixture
def temp_profile_file():
    """Create a temporary profile config file for testing"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as f:
        # Create a basic profile config
        config = {
            "test_profile": [{"name": "test-server", "type": "sse", "url": "http://localhost:8080/sse"}],
            "empty_profile": [],
        }
        f.write(json.dumps(config).encode("utf-8"))
        temp_path = f.name

    yield temp_path
    # Clean up
    os.unlink(temp_path)


@pytest.fixture
def profile_manager(temp_profile_file):
    """Create a ProfileConfigManager with a temp config for testing"""
    return ProfileConfigManager(profile_path=temp_profile_file)


def test_profile_manager_init_default_path():
    """Test that the profile manager initializes with default path"""
    with patch("mcpm.profile.profile_config.os.path.exists", return_value=False):
        manager = ProfileConfigManager()
        assert manager.profile_path == os.path.expanduser("~/.config/mcpm/profiles.json")
        assert manager._profiles == {}


def test_profile_manager_init_custom_path(temp_profile_file):
    """Test that the profile manager initializes with a custom path"""
    manager = ProfileConfigManager(profile_path=temp_profile_file)
    assert manager.profile_path == temp_profile_file
    assert "test_profile" in manager._profiles
    assert "empty_profile" in manager._profiles


def test_load_profiles_not_exists():
    """Test loading profiles when file doesn't exist"""
    with patch("mcpm.profile.profile_config.os.path.exists", return_value=False):
        manager = ProfileConfigManager()
        profiles = manager._load_profiles()
        assert profiles == {}


def test_load_profiles(profile_manager):
    """Test loading profiles from file"""
    profiles = profile_manager._load_profiles()
    assert "test_profile" in profiles
    assert "empty_profile" in profiles
    assert len(profiles["test_profile"]) == 1
    assert len(profiles["empty_profile"]) == 0


def test_new_profile(profile_manager):
    """Test creating a new profile"""
    # Create new profile
    result = profile_manager.new_profile("new_profile")
    assert result is True
    assert "new_profile" in profile_manager._profiles
    assert profile_manager._profiles["new_profile"] == []

    # Test creating existing profile
    result = profile_manager.new_profile("test_profile")
    assert result is False


def test_get_profile(profile_manager):
    """Test getting a profile"""
    # Get existing profile
    profile = profile_manager.get_profile("test_profile")
    assert profile is not None
    assert len(profile) == 1
    assert profile[0].name == "test-server"

    # Get non-existent profile
    profile = profile_manager.get_profile("non_existent")
    assert profile is None


def test_get_profile_server(profile_manager):
    """Test getting a server from a profile"""
    # Get existing server
    server = profile_manager.get_profile_server("test_profile", "test-server")
    assert server is not None
    assert server.name == "test-server"

    # Get non-existent server
    server = profile_manager.get_profile_server("test_profile", "non-existent")
    assert server is None

    # Get server from non-existent profile
    server = profile_manager.get_profile_server("non_existent", "test-server")
    assert server is None


def test_set_profile_new_server(profile_manager):
    """Test setting a new server in a profile"""
    new_server = RemoteServerConfig(name="new-server", url="http://localhost:8081/sse")
    result = profile_manager.set_profile("test_profile", new_server)
    assert result is True

    # Verify server was added
    servers = profile_manager.get_profile("test_profile")
    assert len(servers) == 2
    server_names = [s.name for s in servers]
    assert "new-server" in server_names


def test_set_profile_update_server(profile_manager):
    """Test updating an existing server in a profile"""
    updated_server = RemoteServerConfig(name="test-server", url="http://localhost:8082/sse")
    result = profile_manager.set_profile("test_profile", updated_server)
    assert result is True

    # Verify server was updated
    server = profile_manager.get_profile_server("test_profile", "test-server")
    assert server is not None
    assert server.url == "http://localhost:8082/sse"


def test_set_profile_new_profile(profile_manager):
    """Test setting a server in a new profile"""
    new_server = STDIOServerConfig(name="stdio-server", command="test-command", args=["--arg1", "--arg2"])
    result = profile_manager.set_profile("new_profile", new_server)
    assert result is True

    # Verify profile and server were created
    profile = profile_manager.get_profile("new_profile")
    assert profile is not None
    assert len(profile) == 1
    assert profile[0].name == "stdio-server"


def test_delete_profile(profile_manager):
    """Test deleting a profile"""
    # Delete existing profile
    result = profile_manager.delete_profile("test_profile")
    assert result is True
    assert "test_profile" not in profile_manager._profiles

    # Delete non-existent profile
    result = profile_manager.delete_profile("non_existent")
    assert result is False


def test_list_profiles(profile_manager):
    """Test listing all profiles"""
    profiles = profile_manager.list_profiles()
    assert "test_profile" in profiles
    assert "empty_profile" in profiles
    assert len(profiles["test_profile"]) == 1
    assert len(profiles["empty_profile"]) == 0


def test_rename_profile(profile_manager):
    """Test renaming a profile"""
    # Rename existing profile
    result = profile_manager.rename_profile("test_profile", "renamed_profile")
    assert result is True
    assert "test_profile" not in profile_manager._profiles
    assert "renamed_profile" in profile_manager._profiles

    # Rename to existing profile name
    result = profile_manager.rename_profile("renamed_profile", "empty_profile")
    assert result is False

    # Rename non-existent profile
    result = profile_manager.rename_profile("non_existent", "new_name")
    assert result is False


def test_remove_server(profile_manager):
    """Test removing a server from a profile"""
    # Remove existing server
    result = profile_manager.remove_server("test_profile", "test-server")
    assert result is True

    # Verify server was removed
    profile = profile_manager.get_profile("test_profile")
    assert len(profile) == 0

    # Remove non-existent server
    result = profile_manager.remove_server("test_profile", "non-existent")
    assert result is False

    # Remove from non-existent profile
    result = profile_manager.remove_server("non_existent", "test-server")
    assert result is False


def test_reload(profile_manager):
    """Test reloading profiles from file"""
    # Modify profiles
    profile_manager._profiles = {}
    assert len(profile_manager._profiles) == 0

    # Reload
    profile_manager.reload()
    assert "test_profile" in profile_manager._profiles
    assert "empty_profile" in profile_manager._profiles
