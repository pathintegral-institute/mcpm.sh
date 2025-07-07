import logging
import os
from typing import Dict, List, Optional

from mcpm.core.schema import ProfileMetadata, ServerConfig
from mcpm.global_config import GlobalConfigManager

DEFAULT_PROFILE_PATH = os.path.expanduser("~/.config/mcpm/profiles.json")

logger = logging.getLogger(__name__)


class ProfileConfigManager:
    """
    Profile Config Manager for MCPM v2.0 Virtual Profile System

    This manager provides backward-compatible API while using virtual profiles
    via server tags instead of separate profiles.json file storage.

    Virtual profiles are implemented as tags on servers in the global config.
    Profile metadata (API keys, descriptions) are stored separately.
    """

    def __init__(
        self, profile_path: str = DEFAULT_PROFILE_PATH, global_config_manager: Optional[GlobalConfigManager] = None
    ):
        self.profile_path = os.path.expanduser(profile_path)
        self.global_config = global_config_manager or GlobalConfigManager()

        # Note: Legacy profile migration is now handled by V1ToV2Migrator
        # to ensure it only happens after user confirms migration

    def _load_profiles(self) -> Dict[str, List[ServerConfig]]:
        """Legacy method - now returns virtual profiles from global config."""
        return self.list_profiles()

    def _save_profiles(self) -> None:
        """Legacy method - no-op since virtual profiles auto-save in global config."""
        pass

    def new_profile(self, profile_name: str) -> bool:
        """Create a new profile."""
        # Check if profile already exists (either as metadata or virtual profile)
        if self.global_config.get_profile_metadata(profile_name) or self.global_config.virtual_profile_exists(
            profile_name
        ):
            return False

        # Create profile metadata
        return self.global_config.create_profile_metadata(profile_name)

    def get_profile(self, profile_name: str) -> Optional[List[ServerConfig]]:
        """Get all servers in a profile."""
        # Check if profile exists (either has metadata or virtual servers)
        if not (
            self.global_config.get_profile_metadata(profile_name)
            or self.global_config.virtual_profile_exists(profile_name)
        ):
            return None

        servers = self.global_config.get_servers_by_profile_tag(profile_name)
        return list(servers.values())

    def get_profile_server(self, profile_name: str, server_name: str) -> Optional[ServerConfig]:
        """Get a specific server from a profile."""
        servers = self.global_config.get_servers_by_profile_tag(profile_name)
        return servers.get(server_name)

    def set_profile(self, profile_name: str, config: ServerConfig) -> bool:
        """Add or update a server in a profile."""
        # Ensure profile metadata exists
        if not self.global_config.get_profile_metadata(profile_name):
            self.global_config.create_profile_metadata(profile_name)

        # Add server to global config
        self.global_config.add_server(config, force=True)

        # Tag server with profile
        return self.global_config.add_profile_tag_to_server(config.name, profile_name)

    def delete_profile(self, profile_name: str) -> bool:
        """Delete a profile (removes tags from all servers and deletes metadata)."""
        # Remove profile tag from all servers
        removed_count = self.global_config.delete_virtual_profile(profile_name)

        # Delete profile metadata
        metadata_deleted = self.global_config.delete_profile_metadata(profile_name)

        return removed_count > 0 or metadata_deleted

    def list_profiles(self) -> Dict[str, List[ServerConfig]]:
        """List all profiles and their servers."""
        profiles = {}

        # Get all virtual profiles
        virtual_profiles = self.global_config.get_virtual_profiles()

        # Get all profiles with metadata but no servers
        for metadata in self.global_config.list_profile_metadata().values():
            if metadata.name not in virtual_profiles:
                virtual_profiles[metadata.name] = []

        # Convert to expected format
        for profile_name, server_names in virtual_profiles.items():
            profiles[profile_name] = []
            for server_name in server_names:
                server = self.global_config.get_server(server_name)
                if server:
                    profiles[profile_name].append(server)

        return profiles

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        """Rename a profile."""
        # Check if old profile exists
        if not (
            self.global_config.get_profile_metadata(old_name) or self.global_config.virtual_profile_exists(old_name)
        ):
            return False

        # Check if new name already exists
        if self.global_config.get_profile_metadata(new_name) or self.global_config.virtual_profile_exists(new_name):
            return False

        # Get servers with old profile tag
        servers_to_retag = self.global_config.get_servers_by_profile_tag(old_name)

        # Create new profile metadata
        old_metadata = self.global_config.get_profile_metadata(old_name)
        if old_metadata:
            new_metadata = ProfileMetadata(
                name=new_name, api_key=old_metadata.api_key, description=old_metadata.description
            )
            self.global_config.update_profile_metadata(new_metadata)
        else:
            self.global_config.create_profile_metadata(new_name)

        # Retag all servers
        for server_name in servers_to_retag.keys():
            self.global_config.add_profile_tag_to_server(server_name, new_name)
            self.global_config.remove_profile_tag_from_server(server_name, old_name)

        # Delete old metadata
        self.global_config.delete_profile_metadata(old_name)

        return True

    def remove_server(self, profile_name: str, server_name: str) -> bool:
        """Remove a server from a profile (removes profile tag from server)."""
        return self.global_config.remove_profile_tag_from_server(server_name, profile_name)

    def clear_profile(self, profile_name: str) -> bool:
        """Clear all servers from a profile while keeping the profile metadata."""
        if not (
            self.global_config.get_profile_metadata(profile_name)
            or self.global_config.virtual_profile_exists(profile_name)
        ):
            return False

        # Remove profile tag from all servers
        self.global_config.delete_virtual_profile(profile_name)

        # Ensure profile metadata still exists
        if not self.global_config.get_profile_metadata(profile_name):
            self.global_config.create_profile_metadata(profile_name)

        return True

    def reload(self) -> None:
        """Reload profiles - no-op since virtual profiles are always current."""
        pass

    # New methods for virtual profile system
    def get_profile_metadata(self, profile_name: str) -> Optional[ProfileMetadata]:
        """Get profile metadata (API key, description, etc.)."""
        return self.global_config.get_profile_metadata(profile_name)

    def update_profile_metadata(self, metadata: ProfileMetadata) -> bool:
        """Update profile metadata."""
        return self.global_config.update_profile_metadata(metadata)

    def get_complete_profile(self, profile_name: str) -> Optional[Dict]:
        """Get complete profile info including metadata and servers."""
        return self.global_config.get_complete_profile(profile_name)

    def create_profile(self, profile_name: str, description: str = "") -> bool:
        """Create a new profile with optional description."""
        # Check if profile already exists
        if self.global_config.get_profile_metadata(profile_name) or self.global_config.virtual_profile_exists(
            profile_name
        ):
            return False

        # Create profile metadata with description
        metadata = ProfileMetadata(name=profile_name, description=description)
        return self.global_config.update_profile_metadata(metadata)

    def add_server_to_profile(self, profile_name: str, server_name: str) -> bool:
        """Add an existing global server to a profile by tagging it."""
        # Ensure profile exists
        if not (
            self.global_config.get_profile_metadata(profile_name)
            or self.global_config.virtual_profile_exists(profile_name)
        ):
            self.global_config.create_profile_metadata(profile_name)

        return self.global_config.add_profile_tag_to_server(server_name, profile_name)
