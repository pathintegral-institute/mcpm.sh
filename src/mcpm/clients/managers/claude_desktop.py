"""
Claude Desktop integration utilities for MCP
"""

import logging
import os
from typing import Any, Dict

from mcpm.clients.base import JSONClientManager
from mcpm.core.schema import RemoteServerConfig, ServerConfig
from mcpm.utils.router_server import format_server_url_with_proxy_headers

logger = logging.getLogger(__name__)


class ClaudeDesktopManager(JSONClientManager):
    """Manages Claude Desktop MCP server configurations"""

    # Client information
    client_key = "claude-desktop"
    display_name = "Claude Desktop"
    download_url = "https://claude.ai/download"

    def __init__(self, config_path=None):
        """Initialize the Claude Desktop client manager

        Args:
            config_path: Optional path to the config file. If not provided, uses default path.
        """
        super().__init__()

        if config_path:
            self.config_path = config_path
        else:
            # Set config path based on detected platform
            if self._system == "Darwin":  # macOS
                self.config_path = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
            elif self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("APPDATA", ""), "Claude", "claude_desktop_config.json")
            else:
                # Linux (unsupported by Claude Desktop currently, but future-proofing)
                self.config_path = os.path.expanduser("~/.config/Claude/claude_desktop_config.json")

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Claude Desktop"""
        return {"mcpServers": {}, "disabledServers": {}}

    def disable_server(self, server_name: str) -> bool:
        """Temporarily disable (stash) a server without removing its configuration

        Args:
            server_name: Name of the server to disable

        Returns:
            bool: Success or failure
        """
        config = self._load_config()

        # Check if the server exists in active servers
        if "mcpServers" not in config or server_name not in config["mcpServers"]:
            logger.warning(f"Server '{server_name}' not found in active servers")
            return False

        # Initialize disabledServers if it doesn't exist
        if "disabledServers" not in config:
            config["disabledServers"] = {}

        # Store the server config in disabled servers
        config["disabledServers"][server_name] = config["mcpServers"][server_name]

        # Remove from active servers
        del config["mcpServers"][server_name]

        return self._save_config(config)

    def enable_server(self, server_name: str) -> bool:
        """Re-enable (pop) a previously disabled server

        Args:
            server_name: Name of the server to enable

        Returns:
            bool: Success or failure
        """
        config = self._load_config()

        # Check if the server exists in disabled servers
        if "disabledServers" not in config or server_name not in config["disabledServers"]:
            logger.warning(f"Server '{server_name}' not found in disabled servers")
            return False

        # Initialize mcpServers if it doesn't exist
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        # Move the server config from disabled to active
        config["mcpServers"][server_name] = config["disabledServers"][server_name]

        # Remove from disabled servers
        del config["disabledServers"][server_name]

        return self._save_config(config)

    def is_server_disabled(self, server_name: str) -> bool:
        """Check if a server is currently disabled (stashed)

        Args:
            server_name: Name of the server to check

        Returns:
            bool: True if server is disabled, False otherwise
        """
        config = self._load_config()
        return "disabledServers" in config and server_name in config["disabledServers"]

    def _format_router_server(
        self, profile_name: str, base_url: str, alias_name: str | None = None
    ) -> ServerConfig:
        """Construct a ServerConfig for a router entry.

        The parent JSONClientManager passes in an optional ``alias_name`` which
        should be used as the final server name inside the client config when
        provided.  Accepting the parameter keeps the overriding method
        signature compatible with the base implementation and prevents the
        ``TypeError`` that occurred when ``activate_profile`` tried to forward
        three arguments.
        """
        return format_server_url_with_proxy_headers(
            self.client_key, profile_name, base_url, alias_name
        )

    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        if isinstance(server_config, RemoteServerConfig):
            # use mcp proxy to convert to stdio as sse is not supported for claude desktop yet
            return self.to_client_format(server_config.to_mcp_proxy_stdio())
        return super().to_client_format(server_config)
