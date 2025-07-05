"""
Client configuration management for MCPM
"""

import logging
from typing import List

from mcpm.utils.config import ConfigManager

logger = logging.getLogger(__name__)


class ClientConfigManager:
    """Manages client-specific configuration"""

    def __init__(self):
        """Initialize the client config manager"""
        self.config_manager = ConfigManager()
        self._config = self.config_manager.get_config()

    def _refresh_config(self):
        """Refresh the local config cache from the config manager"""
        self._config = self.config_manager.get_config()

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
