"""
Global server configuration management for MCPM v2.0

This module manages the global server registry where all servers are stored centrally.
Profiles tag servers but don't own them - servers exist globally.
"""

import json
import logging
import os
from typing import Dict, List, Optional

from pydantic import TypeAdapter

from mcpm.core.schema import ProfileMetadata, ServerConfig

DEFAULT_GLOBAL_CONFIG_PATH = os.path.expanduser("~/.config/mcpm/servers.json")
DEFAULT_PROFILE_METADATA_PATH = os.path.expanduser("~/.config/mcpm/profiles_metadata.json")

logger = logging.getLogger(__name__)


class GlobalConfigManager:
    """Manages the global MCPM server configuration.

    In v2.0, all servers are stored in a single global configuration file.
    Profiles organize servers via tagging, but servers exist independently.
    """

    def __init__(
        self, config_path: str = DEFAULT_GLOBAL_CONFIG_PATH, metadata_path: str = DEFAULT_PROFILE_METADATA_PATH
    ):
        self.config_path = os.path.expanduser(config_path)
        self.metadata_path = os.path.expanduser(metadata_path)
        self.config_dir = os.path.dirname(self.config_path)
        self._servers: Dict[str, ServerConfig] = self._load_servers()
        self._profile_metadata: Dict[str, ProfileMetadata] = self._load_profile_metadata()
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Ensure all configuration directories exist"""
        os.makedirs(self.config_dir, exist_ok=True)

    def _load_servers(self) -> Dict[str, ServerConfig]:
        """Load servers from the global configuration file."""
        if not os.path.exists(self.config_path):
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                servers_data = json.load(f) or {}
        except json.JSONDecodeError as e:
            logger.error(f"Error loading global servers from {self.config_path}: {e}")
            return {}

        servers = {}
        for name, config_data in servers_data.items():
            try:
                servers[name] = TypeAdapter(ServerConfig).validate_python(config_data)
            except Exception as e:
                logger.error(f"Error loading server {name}: {e}")
                continue

        return servers

    def _save_servers(self) -> None:
        """Save servers to the global configuration file."""
        self._ensure_dirs()
        servers_data = {name: config.model_dump() for name, config in self._servers.items()}

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(servers_data, f, indent=2)

    def _load_profile_metadata(self) -> Dict[str, ProfileMetadata]:
        """Load profile metadata from the metadata configuration file."""
        if not os.path.exists(self.metadata_path):
            return {}

        try:
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                metadata_data = json.load(f) or {}
        except json.JSONDecodeError as e:
            logger.error(f"Error loading profile metadata from {self.metadata_path}: {e}")
            return {}

        metadata = {}
        for name, meta_data in metadata_data.items():
            try:
                metadata[name] = ProfileMetadata.model_validate(meta_data)
            except Exception as e:
                logger.error(f"Error loading profile metadata {name}: {e}")
                continue

        return metadata

    def _save_profile_metadata(self) -> None:
        """Save profile metadata to the metadata configuration file."""
        self._ensure_dirs()
        metadata_data = {name: meta.model_dump() for name, meta in self._profile_metadata.items()}

        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata_data, f, indent=2)

    def add_server(self, server_config: ServerConfig, force: bool = False) -> bool:
        """Add a server to the global configuration.

        Args:
            server_config: The server configuration to add
            force: Whether to overwrite existing server

        Returns:
            bool: Success or failure
        """
        if server_config.name in self._servers and not force:
            logger.warning(f"Server '{server_config.name}' already exists")
            return False

        self._servers[server_config.name] = server_config
        self._save_servers()
        return True

    def remove_server(self, server_name: str) -> bool:
        """Remove a server from the global configuration.

        Args:
            server_name: Name of the server to remove

        Returns:
            bool: Success or failure
        """
        if server_name not in self._servers:
            logger.warning(f"Server '{server_name}' not found")
            return False

        del self._servers[server_name]
        self._save_servers()
        return True

    def get_server(self, server_name: str) -> Optional[ServerConfig]:
        """Get a server configuration by name.

        Args:
            server_name: Name of the server

        Returns:
            ServerConfig or None if not found
        """
        return self._servers.get(server_name)

    def list_servers(self) -> Dict[str, ServerConfig]:
        """Get all servers in the global configuration.

        Returns:
            Dict mapping server names to configurations
        """
        return self._servers.copy()

    def server_exists(self, server_name: str) -> bool:
        """Check if a server exists in the global configuration.

        Args:
            server_name: Name of the server

        Returns:
            bool: True if server exists
        """
        return server_name in self._servers

    def update_server(self, server_config: ServerConfig) -> bool:
        """Update an existing server configuration.

        Args:
            server_config: Updated server configuration

        Returns:
            bool: Success or failure
        """
        if server_config.name not in self._servers:
            logger.warning(f"Server '{server_config.name}' not found for update")
            return False

        self._servers[server_config.name] = server_config
        self._save_servers()
        return True

    # Virtual Profile Methods
    def get_servers_by_profile_tag(self, profile_tag: str) -> Dict[str, ServerConfig]:
        """Get all servers that have a specific profile tag.

        Args:
            profile_tag: The profile tag to filter by

        Returns:
            Dict mapping server names to configurations that have the tag
        """
        return {name: config for name, config in self._servers.items() if config.has_profile_tag(profile_tag)}

    def add_profile_tag_to_server(self, server_name: str, profile_tag: str) -> bool:
        """Add a profile tag to a specific server.

        Args:
            server_name: Name of the server
            profile_tag: Profile tag to add

        Returns:
            bool: Success or failure
        """
        if server_name not in self._servers:
            logger.warning(f"Server '{server_name}' not found")
            return False

        self._servers[server_name].add_profile_tag(profile_tag)
        self._save_servers()
        return True

    def remove_profile_tag_from_server(self, server_name: str, profile_tag: str) -> bool:
        """Remove a profile tag from a specific server.

        Args:
            server_name: Name of the server
            profile_tag: Profile tag to remove

        Returns:
            bool: Success or failure
        """
        if server_name not in self._servers:
            logger.warning(f"Server '{server_name}' not found")
            return False

        self._servers[server_name].remove_profile_tag(profile_tag)
        self._save_servers()
        return True

    def get_all_profile_tags(self) -> List[str]:
        """Get all unique profile tags across all servers.

        Returns:
            List of unique profile tag names
        """
        all_tags = set()
        for config in self._servers.values():
            all_tags.update(config.profile_tags)
        return sorted(list(all_tags))

    def get_virtual_profiles(self) -> Dict[str, List[str]]:
        """Get all virtual profiles and their associated server names.

        Returns:
            Dict mapping profile names to lists of server names
        """
        profiles = {}
        for server_name, config in self._servers.items():
            for tag in config.profile_tags:
                if tag not in profiles:
                    profiles[tag] = []
                profiles[tag].append(server_name)
        return profiles

    def delete_virtual_profile(self, profile_tag: str) -> int:
        """Delete a virtual profile by removing the tag from all servers.

        Args:
            profile_tag: Profile tag to remove from all servers

        Returns:
            int: Number of servers that had the tag removed
        """
        count = 0
        for config in self._servers.values():
            if config.has_profile_tag(profile_tag):
                config.remove_profile_tag(profile_tag)
                count += 1

        if count > 0:
            self._save_servers()

        return count

    def virtual_profile_exists(self, profile_tag: str) -> bool:
        """Check if a virtual profile exists (has any servers with the tag).

        Args:
            profile_tag: Profile tag to check

        Returns:
            bool: True if any server has this tag
        """
        return any(config.has_profile_tag(profile_tag) for config in self._servers.values())

    # Profile Metadata Methods
    def create_profile_metadata(
        self, name: str, api_key: Optional[str] = None, description: Optional[str] = None
    ) -> bool:
        """Create profile metadata.

        Args:
            name: Profile name
            api_key: Optional API key for sharing
            description: Optional profile description

        Returns:
            bool: Success or failure
        """
        if name in self._profile_metadata:
            logger.warning(f"Profile metadata '{name}' already exists")
            return False

        self._profile_metadata[name] = ProfileMetadata(name=name, api_key=api_key, description=description)
        self._save_profile_metadata()
        return True

    def get_profile_metadata(self, name: str) -> Optional[ProfileMetadata]:
        """Get profile metadata by name.

        Args:
            name: Profile name

        Returns:
            ProfileMetadata or None if not found
        """
        return self._profile_metadata.get(name)

    def update_profile_metadata(self, metadata: ProfileMetadata) -> bool:
        """Update profile metadata.

        Args:
            metadata: Updated profile metadata

        Returns:
            bool: Success or failure
        """
        self._profile_metadata[metadata.name] = metadata
        self._save_profile_metadata()
        return True

    def delete_profile_metadata(self, name: str) -> bool:
        """Delete profile metadata.

        Args:
            name: Profile name

        Returns:
            bool: Success or failure
        """
        if name not in self._profile_metadata:
            logger.warning(f"Profile metadata '{name}' not found")
            return False

        del self._profile_metadata[name]
        self._save_profile_metadata()
        return True

    def list_profile_metadata(self) -> Dict[str, ProfileMetadata]:
        """Get all profile metadata.

        Returns:
            Dict mapping profile names to metadata
        """
        return self._profile_metadata.copy()

    def get_complete_profile(self, name: str) -> Optional[Dict[str, any]]:
        """Get complete profile information including metadata and servers.

        Args:
            name: Profile name

        Returns:
            Dict with metadata and servers, or None if profile doesn't exist
        """
        # Check if profile exists either as metadata or virtual profile
        metadata = self.get_profile_metadata(name)
        servers = self.get_servers_by_profile_tag(name)

        if not metadata and not servers:
            return None

        return {
            "name": name,
            "metadata": metadata.model_dump() if metadata else {"name": name},
            "servers": [config.model_dump() for config in servers.values()],
        }
