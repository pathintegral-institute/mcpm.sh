"""
Tests for the profile module - Updated for Virtual Profile System
"""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from mcpm.core.schema import STDIOServerConfig
from mcpm.global_config import GlobalConfigManager
from mcpm.profile.profile_config import ProfileConfigManager


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing virtual profiles"""
    with tempfile.TemporaryDirectory() as temp_dir:
        servers_path = os.path.join(temp_dir, "servers.json")
        metadata_path = os.path.join(temp_dir, "profiles_metadata.json")
        legacy_path = os.path.join(temp_dir, "profiles.json")
        yield temp_dir, servers_path, metadata_path, legacy_path


@pytest.fixture
def global_config(temp_dirs):
    """Create a GlobalConfigManager with temporary files"""
    temp_dir, servers_path, metadata_path, legacy_path = temp_dirs
    return GlobalConfigManager(config_path=servers_path, metadata_path=metadata_path)


@pytest.fixture
def profile_manager_clean(global_config, temp_dirs):
    """Create a ProfileConfigManager with clean temp files"""
    temp_dir, servers_path, metadata_path, legacy_path = temp_dirs
    return ProfileConfigManager(profile_path=legacy_path, global_config_manager=global_config)


@pytest.fixture
def profile_manager_with_legacy(temp_dirs):
    """Create a ProfileConfigManager that will migrate legacy profiles"""
    temp_dir, servers_path, metadata_path, legacy_path = temp_dirs

    # Create legacy profiles.json file
    legacy_config = {
        "test_profile": [{"name": "test-server", "url": "http://localhost:8080/sse", "headers": {}}],
        "empty_profile": [],
    }
    with open(legacy_path, "w") as f:
        json.dump(legacy_config, f)

    # Create managers - should trigger migration
    global_config = GlobalConfigManager(config_path=servers_path, metadata_path=metadata_path)
    return ProfileConfigManager(profile_path=legacy_path, global_config_manager=global_config)


def test_profile_manager_init_default_path():
    """Test that the profile manager initializes with default path"""
    with patch("mcpm.profile.profile_config.os.path.exists", return_value=False):
        manager = ProfileConfigManager()
        assert manager.profile_path == os.path.expanduser("~/.config/mcpm/profiles.json")


def test_profile_manager_init_custom_path(profile_manager_clean, temp_dirs):
    """Test that the profile manager initializes with a custom path"""
    temp_dir, servers_path, metadata_path, legacy_path = temp_dirs
    manager = profile_manager_clean
    assert manager.profile_path == legacy_path


def test_legacy_migration(profile_manager_with_legacy, temp_dirs):
    """Test that legacy profiles.json is NOT automatically migrated"""
    temp_dir, servers_path, metadata_path, legacy_path = temp_dirs
    manager = profile_manager_with_legacy

    # Check that legacy file still exists (no auto-migration)
    assert os.path.exists(legacy_path)
    assert not os.path.exists(legacy_path + ".backup")

    # Check that profiles were NOT migrated automatically
    profiles = manager.list_profiles()
    assert len(profiles) == 0  # No profiles should exist yet

    # Legacy migration is now handled by V1ToV2Migrator, not ProfileConfigManager


def test_new_profile(profile_manager_clean):
    """Test creating a new profile"""
    manager = profile_manager_clean

    # Create new profile
    result = manager.new_profile("new_profile")
    assert result is True

    # Profile should exist and be empty
    profile = manager.get_profile("new_profile")
    assert profile == []

    # Test creating existing profile
    result = manager.new_profile("new_profile")
    assert result is False


def test_get_profile(profile_manager_clean):
    """Test getting a profile"""
    manager = profile_manager_clean

    # Create profile with server
    manager.new_profile("test_profile")
    server_config = STDIOServerConfig(name="test-server", command="echo")
    manager.set_profile("test_profile", server_config)

    # Get existing profile
    profile = manager.get_profile("test_profile")
    assert profile is not None
    assert len(profile) == 1
    assert profile[0].name == "test-server"

    # Get non-existent profile
    profile = manager.get_profile("non_existent")
    assert profile is None


def test_get_profile_server(profile_manager_clean):
    """Test getting a server from a profile"""
    manager = profile_manager_clean

    # Create profile with server
    manager.new_profile("test_profile")
    server_config = STDIOServerConfig(name="test-server", command="echo")
    manager.set_profile("test_profile", server_config)

    # Get existing server
    server = manager.get_profile_server("test_profile", "test-server")
    assert server is not None
    assert server.name == "test-server"

    # Get non-existent server
    server = manager.get_profile_server("test_profile", "non-existent")
    assert server is None

    # Get server from non-existent profile
    server = manager.get_profile_server("non_existent", "test-server")
    assert server is None


def test_set_profile(profile_manager_clean):
    """Test adding a server to a profile"""
    manager = profile_manager_clean

    # Add server to new profile (should create profile)
    server_config = STDIOServerConfig(name="new-server", command="echo")
    result = manager.set_profile("new_profile", server_config)
    assert result is True

    # Profile should exist with server
    profile = manager.get_profile("new_profile")
    assert len(profile) == 1
    assert profile[0].name == "new-server"

    # Add another server
    server_config2 = STDIOServerConfig(name="second-server", command="cat")
    manager.set_profile("new_profile", server_config2)

    profile = manager.get_profile("new_profile")
    assert len(profile) == 2


def test_delete_profile(profile_manager_clean):
    """Test deleting a profile"""
    manager = profile_manager_clean

    # Create profile with server
    manager.new_profile("test_profile")
    server_config = STDIOServerConfig(name="test-server", command="echo")
    manager.set_profile("test_profile", server_config)

    # Delete profile
    result = manager.delete_profile("test_profile")
    assert result is True

    # Profile should not exist
    profile = manager.get_profile("test_profile")
    assert profile is None

    # Server should still exist in global config
    server = manager.global_config.get_server("test-server")
    assert server is not None
    assert not server.has_profile_tag("test_profile")

    # Delete non-existent profile
    result = manager.delete_profile("non_existent")
    assert result is False


def test_list_profiles(profile_manager_clean):
    """Test listing profiles"""
    manager = profile_manager_clean

    # Initially no profiles
    profiles = manager.list_profiles()
    assert profiles == {}

    # Create profiles
    manager.new_profile("profile1")
    manager.new_profile("profile2")

    server1 = STDIOServerConfig(name="server1", command="echo")
    server2 = STDIOServerConfig(name="server2", command="cat")

    manager.set_profile("profile1", server1)
    manager.set_profile("profile2", server2)

    profiles = manager.list_profiles()
    assert len(profiles) == 2
    assert "profile1" in profiles
    assert "profile2" in profiles
    assert len(profiles["profile1"]) == 1
    assert len(profiles["profile2"]) == 1


def test_rename_profile(profile_manager_clean):
    """Test renaming a profile"""
    manager = profile_manager_clean

    # Create profile with server
    manager.new_profile("old_name")
    server_config = STDIOServerConfig(name="test-server", command="echo")
    manager.set_profile("old_name", server_config)

    # Rename profile
    result = manager.rename_profile("old_name", "new_name")
    assert result is True

    # Old profile should not exist
    assert manager.get_profile("old_name") is None

    # New profile should exist with same servers
    new_profile = manager.get_profile("new_name")
    assert len(new_profile) == 1
    assert new_profile[0].name == "test-server"

    # Server should have new profile tag
    server = manager.global_config.get_server("test-server")
    assert server.has_profile_tag("new_name")
    assert not server.has_profile_tag("old_name")


def test_remove_server(profile_manager_clean):
    """Test removing a server from a profile"""
    manager = profile_manager_clean

    # Create profile with servers
    manager.new_profile("test_profile")
    server1 = STDIOServerConfig(name="server1", command="echo")
    server2 = STDIOServerConfig(name="server2", command="cat")

    manager.set_profile("test_profile", server1)
    manager.set_profile("test_profile", server2)

    # Remove one server
    result = manager.remove_server("test_profile", "server1")
    assert result is True

    # Profile should have one server
    profile = manager.get_profile("test_profile")
    assert len(profile) == 1
    assert profile[0].name == "server2"

    # Server should still exist globally but without profile tag
    server = manager.global_config.get_server("server1")
    assert server is not None
    assert not server.has_profile_tag("test_profile")


def test_clear_profile(profile_manager_clean):
    """Test clearing all servers from a profile"""
    manager = profile_manager_clean

    # Create profile with servers
    manager.new_profile("test_profile")
    server1 = STDIOServerConfig(name="server1", command="echo")
    server2 = STDIOServerConfig(name="server2", command="cat")

    manager.set_profile("test_profile", server1)
    manager.set_profile("test_profile", server2)

    # Clear profile
    result = manager.clear_profile("test_profile")
    assert result is True

    # Profile should exist but be empty
    profile = manager.get_profile("test_profile")
    assert profile == []

    # Servers should still exist globally
    assert manager.global_config.get_server("server1") is not None
    assert manager.global_config.get_server("server2") is not None


def test_virtual_profile_features(profile_manager_clean):
    """Test virtual profile specific features"""
    manager = profile_manager_clean

    # Create server that belongs to multiple profiles
    server_config = STDIOServerConfig(name="shared-server", command="echo")

    manager.set_profile("profile1", server_config)
    manager.add_server_to_profile("profile2", "shared-server")

    # Server should appear in both profiles
    profile1 = manager.get_profile("profile1")
    profile2 = manager.get_profile("profile2")

    assert len(profile1) == 1
    assert len(profile2) == 1
    assert profile1[0].name == "shared-server"
    assert profile2[0].name == "shared-server"

    # Server should have both profile tags
    server = manager.global_config.get_server("shared-server")
    assert server.has_profile_tag("profile1")
    assert server.has_profile_tag("profile2")


def test_profile_metadata(profile_manager_clean):
    """Test profile metadata functionality"""
    manager = profile_manager_clean

    # Create profile and update metadata
    manager.new_profile("api_profile")

    metadata = manager.get_profile_metadata("api_profile")
    assert metadata is not None
    assert metadata.name == "api_profile"
    assert metadata.api_key is None

    # Update metadata
    from mcpm.core.schema import ProfileMetadata

    new_metadata = ProfileMetadata(name="api_profile", api_key="sk-test-123", description="Test profile")
    manager.update_profile_metadata(new_metadata)

    # Retrieve updated metadata
    updated_metadata = manager.get_profile_metadata("api_profile")
    assert updated_metadata.api_key == "sk-test-123"
    assert updated_metadata.description == "Test profile"


def test_reload_does_nothing(profile_manager_clean):
    """Test that reload is a no-op for virtual profiles"""
    manager = profile_manager_clean

    # This should not raise an error
    manager.reload()
    assert True  # Test passes if no exception is raised
