import logging
from typing import Any, Optional

import pydantic
from pydantic import BaseModel, Field

from mcpm.router.base import MCPRouterProtocol
from mcpm.router.connection_types import ConnectionDetails, ConnectionType, SSEConnectionDetails, StdioConnectionDetails
from mcpm.utils.config import ConfigManager

logger = logging.getLogger(__name__)


class Profile(BaseModel):
    # profile only maintains the server_id ref, don't create client session
    name: str = Field(..., description="Profile name")
    servers: list[ConnectionDetails] = Field(..., description="List of servers connection arguments")


# TODO: from profile.json
class ProfileManager:
    def __init__(self, router: MCPRouterProtocol):
        self._config_manager = ConfigManager()
        self.profiles: dict[str, Profile] = {}
        self.router = router
        self._load_profiles_from_config()

    def _load_profiles_from_config(self) -> None:
        """Load all profiles from the configuration file."""
        config = self._config_manager.get_config()
        profiles_config: dict[str, list[dict[str, Any]]] = config.get("profiles", {})

        # Clear existing profiles if any
        if self.profiles:
            self.profiles.clear()

        # Process each profile in the configuration
        for profile_name, servers_config in profiles_config.items():
            self._process_profile(profile_name, servers_config)

    def _process_profile(self, profile_name: str, servers_config: list[dict[str, Any]]) -> None:
        """Process a single profile configuration and create a Profile object."""
        servers: list[ConnectionDetails] = []

        for server_config in servers_config:
            server = self._create_server_connection(profile_name, server_config)
            if server:
                servers.append(server)

        if servers:
            self.profiles[profile_name] = Profile(name=profile_name, servers=servers)
            logger.info(f"Processed profile {profile_name} with {len(servers)} servers")

    def _create_server_connection(
        self, profile_name: str, server_config: dict[str, Any]
    ) -> Optional[ConnectionDetails]:
        """Create a server connection from configuration."""
        try:
            # Ensure server has an ID (using name as fallback)
            if "id" not in server_config and "name" in server_config:
                server_config["id"] = server_config["name"]

            server_type = server_config.get("type")

            if server_type == ConnectionType.STDIO:
                return StdioConnectionDetails.model_validate(server_config)
            elif server_type == ConnectionType.SSE:
                return SSEConnectionDetails.model_validate(server_config)
            else:
                logger.warning(f"Unsupported server type '{server_type}' in profile {profile_name}")
                return None

        except pydantic.ValidationError as e:
            logger.warning(f"Invalid server configuration for profile {profile_name}: {server_config}, error: {e}")
            return None

    # on initialization
    def initialize_servers(self) -> list[ConnectionDetails]:
        """Initialize all servers from loaded profiles."""

        # Register unique servers with the router
        servers: list[ConnectionDetails] = []
        servers_set: set[str] = set()
        for profile in self.profiles.values():
            for server in profile.servers:
                # make integrate with router
                if server.id not in servers_set:
                    # if fail just skip
                    servers.append(server)
                    servers_set.add(server.id)

        return servers

    # on updating
    async def update_profile(self, profile_name: str) -> Optional[Profile]:
        """
        Update a profile by name, loading its configuration and registering servers.
        Returns the Profile object if successful, None otherwise.
        """
        config = self._config_manager.get_config()
        profiles_config: dict[str, list[dict[str, Any]]] = config.get("profiles", {})

        if profile_name not in profiles_config:
            logger.warning(f"Profile '{profile_name}' not found in configuration")
            return None

        # Process the profile configuration
        self._process_profile(profile_name, profiles_config[profile_name])

        if profile_name not in self.profiles:
            logger.warning(f"Failed to process profile '{profile_name}'")
            return None

        # Register servers with the router
        profile = self.profiles[profile_name]
        for server in profile.servers:
            if server.id not in self.router.server_sessions.keys():
                await self.router.add_server(server.id, server)

        return profile

    def get_profile_server_ids(self, profile_name: str) -> list[str]:
        if profile_name not in self.profiles:
            return []

        return [server.id for server in self.profiles[profile_name].servers]
