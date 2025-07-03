"""
Tests for the new virtual profile system
"""

import os
import tempfile

import pytest

from mcpm.core.schema import ProfileMetadata, STDIOServerConfig
from mcpm.global_config import GlobalConfigManager
from mcpm.profile.profile_config import ProfileConfigManager


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        servers_path = os.path.join(temp_dir, "servers.json")
        metadata_path = os.path.join(temp_dir, "profiles_metadata.json")
        yield temp_dir, servers_path, metadata_path


@pytest.fixture
def global_config(temp_dirs):
    """Create a GlobalConfigManager with temporary files"""
    temp_dir, servers_path, metadata_path = temp_dirs
    return GlobalConfigManager(config_path=servers_path, metadata_path=metadata_path)


@pytest.fixture
def profile_manager(global_config):
    """Create a ProfileConfigManager with the global config"""
    return ProfileConfigManager(global_config_manager=global_config)


def test_virtual_profile_creation(profile_manager):
    """Test creating a virtual profile"""
    # Create a new profile
    assert profile_manager.new_profile("test-profile")

    # Profile should exist but be empty
    servers = profile_manager.get_profile("test-profile")
    assert servers == []

    # Should not be able to create duplicate
    assert not profile_manager.new_profile("test-profile")


def test_adding_server_to_virtual_profile(profile_manager, global_config):
    """Test adding a server to a virtual profile"""
    # Create a server
    server_config = STDIOServerConfig(name="test-server", command="echo", args=["hello"], profile_tags=[])

    # Create profile and add server
    profile_manager.new_profile("web-dev")
    assert profile_manager.set_profile("web-dev", server_config)

    # Verify server is in profile
    servers = profile_manager.get_profile("web-dev")
    assert len(servers) == 1
    assert servers[0].name == "test-server"

    # Verify server has profile tag
    global_server = global_config.get_server("test-server")
    assert global_server.has_profile_tag("web-dev")


def test_server_in_multiple_profiles(profile_manager):
    """Test that a server can belong to multiple profiles"""
    # Create server
    server_config = STDIOServerConfig(name="shared-server", command="echo", args=["shared"])

    # Create two profiles and add same server to both
    profile_manager.new_profile("profile-1")
    profile_manager.new_profile("profile-2")

    profile_manager.set_profile("profile-1", server_config)
    profile_manager.add_server_to_profile("profile-2", "shared-server")

    # Verify server appears in both profiles
    profile1_servers = profile_manager.get_profile("profile-1")
    profile2_servers = profile_manager.get_profile("profile-2")

    assert len(profile1_servers) == 1
    assert len(profile2_servers) == 1
    assert profile1_servers[0].name == "shared-server"
    assert profile2_servers[0].name == "shared-server"


def test_profile_metadata(profile_manager):
    """Test profile metadata functionality"""
    # Create profile with metadata
    profile_manager.new_profile("api-profile")

    # Update metadata
    metadata = ProfileMetadata(name="api-profile", api_key="sk-test-123", description="Profile for API testing")
    assert profile_manager.update_profile_metadata(metadata)

    # Retrieve metadata
    retrieved = profile_manager.get_profile_metadata("api-profile")
    assert retrieved is not None
    assert retrieved.api_key == "sk-test-123"
    assert retrieved.description == "Profile for API testing"


def test_profile_deletion(profile_manager, global_config):
    """Test deleting a profile removes tags but keeps servers"""
    # Create server and profile
    server_config = STDIOServerConfig(name="test-server", command="echo")
    profile_manager.new_profile("temp-profile")
    profile_manager.set_profile("temp-profile", server_config)

    # Verify setup
    assert len(profile_manager.get_profile("temp-profile")) == 1
    assert global_config.get_server("test-server").has_profile_tag("temp-profile")

    # Delete profile
    assert profile_manager.delete_profile("temp-profile")

    # Profile should be gone
    assert profile_manager.get_profile("temp-profile") is None

    # Server should still exist but without the tag
    server = global_config.get_server("test-server")
    assert server is not None
    assert not server.has_profile_tag("temp-profile")


def test_list_profiles(profile_manager):
    """Test listing all profiles"""
    # Create multiple profiles with servers
    profile_manager.new_profile("profile-a")
    profile_manager.new_profile("profile-b")

    server1 = STDIOServerConfig(name="server-1", command="echo")
    server2 = STDIOServerConfig(name="server-2", command="cat")

    profile_manager.set_profile("profile-a", server1)
    profile_manager.set_profile("profile-b", server2)

    # List profiles
    profiles = profile_manager.list_profiles()

    assert "profile-a" in profiles
    assert "profile-b" in profiles
    assert len(profiles["profile-a"]) == 1
    assert len(profiles["profile-b"]) == 1
    assert profiles["profile-a"][0].name == "server-1"
    assert profiles["profile-b"][0].name == "server-2"


def test_complete_profile_info(profile_manager):
    """Test getting complete profile information"""
    # Create profile with metadata and server
    profile_manager.new_profile("complete-profile")

    metadata = ProfileMetadata(name="complete-profile", api_key="sk-complete-123", description="Complete test profile")
    profile_manager.update_profile_metadata(metadata)

    server = STDIOServerConfig(name="complete-server", command="echo")
    profile_manager.set_profile("complete-profile", server)

    # Get complete info
    complete = profile_manager.get_complete_profile("complete-profile")

    assert complete is not None
    assert complete["name"] == "complete-profile"
    assert complete["metadata"]["api_key"] == "sk-complete-123"
    assert len(complete["servers"]) == 1
    assert complete["servers"][0]["name"] == "complete-server"


def test_no_data_duplication(profile_manager, global_config):
    """Test that servers are not duplicated between global config and profiles"""
    # Create server and add to profile
    server_config = STDIOServerConfig(name="unique-server", command="echo")
    profile_manager.new_profile("test-profile")
    profile_manager.set_profile("test-profile", server_config)

    # Get server from global config and profile
    global_server = global_config.get_server("unique-server")
    profile_servers = profile_manager.get_profile("test-profile")

    # Should be the same server object data
    assert global_server.name == profile_servers[0].name
    assert global_server.command == profile_servers[0].command
    assert global_server.has_profile_tag("test-profile")
