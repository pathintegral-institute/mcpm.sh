"""Trae integration utilities for MCP"""

import logging
import os
from typing import Any, Dict

from mcpm.clients.base import JSONClientManager
from mcpm.core.schema import ServerConfig

logger = logging.getLogger(__name__)


class TraeManager(JSONClientManager):
    """Manages Trae MCP server configurations"""

    # Client information
    client_key = "trae"
    display_name = "Trae"
    download_url = "https://trae.ai/"

    def __init__(self, config_path=None):
        """Initialize the Trae client manager

        Args:
            config_path: Optional path to the config file. If not provided, uses default path.
        """
        super().__init__()

        if config_path:
            self.config_path = config_path
        else:
            # Set config path based on detected platform
            if self._system == "Darwin":  # macOS
                self.config_path = os.path.expanduser("~/Library/Application Support/Trae/User/mcp.json")
            elif self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("APPDATA", ""), "Trae", "User", "mcp.json")
            else:
                # Linux
                self.config_path = os.path.expanduser("~/.config/trae/mcp.json")
                logger.warning("Trae is not supported on Linux yet.")

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Trae"""
        return {"mcpServers": {}}

    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert ServerConfig to Trae-specific format

        Args:
            server_config: ServerConfig object

        Returns:
            Dict containing Trae-specific configuration
        """
        # Start with the standard conversion
        result = super().to_client_format(server_config)

        # the fromGalleryId field is Trae-specific and not supported yet

        return result

    def from_client_format(self, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert Trae format to ServerConfig

        Args:
            server_name: Name of the server
            client_config: Trae-specific configuration

        Returns:
            ServerConfig object
        """
        # Make a copy of the config to avoid modifying the original
        config_copy = client_config.copy()

        return super().from_client_format(server_name, config_copy)
