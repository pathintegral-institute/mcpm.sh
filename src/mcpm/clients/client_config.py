"""
Client configuration management for MCPM
"""

import logging
from typing import Any, Dict, List, Optional

from mcpm.utils.config import ConfigManager
from mcpm.utils.scope import ScopeType, extract_from_scope

logger = logging.getLogger(__name__)


class ClientConfigManager:
    """Manages client-specific configuration including active client and stashed servers"""

    def __init__(self):
        """Initialize the client config manager"""
        self.config_manager = ConfigManager()
        self._config = self.config_manager.get_config()

    def _refresh_config(self):
        """Refresh the local config cache from the config manager"""
        self._config = self.config_manager.get_config()

    def get_active_client(self) -> str | None:
        target = self.get_active_target()
        if not target:
            return
        scope_type, scope = extract_from_scope(target)
        if scope_type != ScopeType.CLIENT:
            return
        return scope

    def set_active_target(self, target_name: str | None) -> bool:
        """Set the active target

        Args:
            target_name: Name of target to set as active

        Returns:
            bool: Success or failure
        """
        # Set the active target
        result = self.config_manager.set_config("active_target", target_name)
        self._refresh_config()
        return result

    def get_active_target(self) -> str | None:
        """Get the name of the currently active target or None if not set"""
        self._refresh_config()
        return self._config.get("active_target")

    def get_active_profile(self) -> str | None:
        target = self.get_active_target()
        if not target:
            return
        scope_type, scope = extract_from_scope(target)
        if scope_type != ScopeType.PROFILE:
            return
        return scope

    def get_supported_clients(self) -> List[str]:
        """Get a list of supported client names"""
        # Import here to avoid circular imports
        from mcpm.clients.client_registry import ClientRegistry

        return ClientRegistry.get_supported_clients()

    def get_client_manager(self, client_name: str):
        """Get the appropriate client manager for a client

        Args:
            client_name: Name of the client

        Returns:
            BaseClientManager or None if client not supported
        """
        # Import here to avoid circular imports
        from mcpm.clients.client_registry import ClientRegistry

        return ClientRegistry.get_client_manager(client_name)

    def stash_server(self, scope_name: str, server_name: str, server_config: Any) -> bool:
        """Store a disabled server configuration in the global config

        Args:
            scope_name: Name of the scope the server belongs to
            server_name: Name of the server to stash
            server_config: Server configuration to stash (ServerConfig object or dict)

        Returns:
            bool: Success or failure
        """
        # Refresh config to ensure we have the latest state
        self._refresh_config()

        # Ensure stashed_servers section exists
        if "stashed_servers" not in self._config:
            self._config["stashed_servers"] = {}

        # Ensure client section exists
        if scope_name not in self._config["stashed_servers"]:
            self._config["stashed_servers"][scope_name] = {}

        # Convert ServerConfig to dict if needed
        try:
            # If it's a ServerConfig object with to_dict method
            if hasattr(server_config, "to_dict") and callable(server_config.to_dict):
                server_dict = server_config.to_dict()
            else:
                # Assume it's already a dict or JSON serializable
                server_dict = server_config

            # Add the server configuration
            stashed_servers = self._config.get("stashed_servers", {})
            if scope_name not in stashed_servers:
                stashed_servers[scope_name] = {}
            stashed_servers[scope_name][server_name] = server_dict

            # Use set_config to save the updated stashed_servers
            result = self.config_manager.set_config("stashed_servers", stashed_servers)
            self._refresh_config()
            return result
        except Exception as e:
            logger.error(f"Failed to save stashed server: {e}")
            return False

    def pop_server(self, scope_name: str, server_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stashed server configuration from the global config

        Args:
            scope_name: Name of the scope the server belongs to
            server_name: Name of the server to retrieve

        Returns:
            Dict: Server configuration or None if not found
        """
        # Refresh config to ensure we have the latest state
        self._refresh_config()

        # Check if stashed_servers section exists
        stashed_servers = self._config.get("stashed_servers", {})
        if not stashed_servers:
            return None

        # Check if scope section exists
        if scope_name not in stashed_servers:
            return None

        # Check if server exists
        if server_name not in stashed_servers[scope_name]:
            return None

        # Get the server configuration
        server_config = stashed_servers[scope_name][server_name]

        # Remove the server from stashed servers
        del stashed_servers[scope_name][server_name]

        # Clean up empty scope section if needed
        if not stashed_servers[scope_name]:
            del stashed_servers[scope_name]

        # Clean up empty stashed_servers section if needed
        if not stashed_servers:
            # Set to None to remove the key completely
            self.config_manager.set_config("stashed_servers", None)
        else:
            # Update with modified stashed_servers
            self.config_manager.set_config("stashed_servers", stashed_servers)

        # Refresh config after changes
        self._refresh_config()

        return server_config

    def is_server_stashed(self, scope_name: str, server_name: str) -> bool:
        """Check if a server is stashed in the global config

        Args:
            scope_name: Name of the scope the server belongs to
            server_name: Name of the server to check

        Returns:
            bool: True if server is stashed, False otherwise
        """
        # Refresh config to ensure we have the latest state
        self._refresh_config()

        # Check if stashed_servers section exists
        stashed_servers = self._config.get("stashed_servers", {})
        if not stashed_servers:
            return False

        # Check if scope section exists
        if scope_name not in stashed_servers:
            return False

        # Check if server exists
        return server_name in stashed_servers[scope_name]

    def get_stashed_servers(self, scope_name: str) -> Dict[str, Dict[str, Any]]:
        """Get all stashed servers for a client

        Args:
            scope_name: Name of the scope to get stashed servers for

        Returns:
            Dict: Dictionary of server configurations by name
        """
        # Refresh config to ensure we have the latest state
        self._refresh_config()

        # Check if stashed_servers section exists
        stashed_servers = self._config.get("stashed_servers", {})
        if not stashed_servers:
            return {}

        # Check if scope section exists
        if scope_name not in stashed_servers:
            return {}

        return stashed_servers[scope_name]
