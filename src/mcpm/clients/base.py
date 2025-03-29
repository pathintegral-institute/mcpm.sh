"""
Base client manager module that defines the interface for all client managers.
"""

import os
import json
import logging
import platform
from typing import Dict, Optional, Any, List, Union

from mcpm.utils.server_config import ServerConfig

logger = logging.getLogger(__name__)


class BaseClientManager:
    """Base class for all client managers providing a common interface"""

    # Client information properties
    client_key = ""  # Client identifier (e.g., "claude-desktop")
    display_name = ""  # Human-readable name (e.g., "Claude Desktop")
    download_url = ""  # URL to download the client

    def __init__(self):
        """Initialize the client manager"""
        self.config_path = None  # To be set by subclasses
        self._config = None
        self._system = platform.system()

    def _load_config(self) -> Dict[str, Any]:
        """Load client configuration file

        Returns:
            Dict containing the client configuration with at least {"mcpServers": {}}
        """
        # Create empty config with the correct structure
        empty_config = {"mcpServers": {}}

        if not os.path.exists(self.config_path):
            logger.warning(f"Client config file not found at: {self.config_path}")
            return empty_config

        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
                # Ensure mcpServers section exists
                if "mcpServers" not in config:
                    config["mcpServers"] = {}
                return config
        except json.JSONDecodeError:
            logger.error(f"Error parsing client config file: {self.config_path}")

            # Backup the corrupt file
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.bak"
                try:
                    os.rename(self.config_path, backup_path)
                    logger.info(f"Backed up corrupt config file to: {backup_path}")
                except Exception as e:
                    logger.error(f"Failed to backup corrupt file: {str(e)}")

            # Return empty config
            return empty_config

    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to client config file

        Args:
            config: Configuration to save

        Returns:
            bool: Success or failure
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            with open(self.config_path, "w") as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving client config: {str(e)}")
            return False

    def get_servers(self) -> Dict[str, Any]:
        """Get all MCP servers configured for this client

        Returns:
            Dict of server configurations by name
        """
        # To be overridden by subclasses
        config = self._load_config()
        return config.get("mcpServers", {})

    def get_server(self, server_name: str) -> Optional[ServerConfig]:
        """Get a server configuration

        Args:
            server_name: Name of the server

        Returns:
            ServerConfig object if found, None otherwise
        """
        servers = self.get_servers()

        # Check if the server exists
        if server_name not in servers:
            logger.debug(f"Server {server_name} not found in {self.display_name} config")
            return None

        # Get the server config and convert to ServerConfig
        client_config = servers[server_name]
        return self.from_client_format(server_name, client_config)

    def add_server(self, server_config: Union[ServerConfig, Dict[str, Any]], name: Optional[str] = None) -> bool:
        """Add or update a server in the client config

        Can accept either a ServerConfig object or a raw dictionary in client format.
        When using a dictionary, a name must be provided.

        Args:
            server_config: ServerConfig object or dictionary in client format
            name: Required server name when using dictionary format

        Returns:
            bool: Success or failure
        """
        # Handle direct dictionary input
        if isinstance(server_config, dict):
            if name is None:
                raise ValueError("Name must be provided when using dictionary format")
            server_name = name
            client_config = server_config  # Already in client format
        # Handle ServerConfig objects
        else:
            server_name = server_config.name
            client_config = self.to_client_format(server_config)

        # Update config directly
        config = self._load_config()
        config["mcpServers"][server_name] = client_config

        return self._save_config(config)

    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert ServerConfig to client-specific format with common core fields

        This base implementation provides the common core fields (command, args, env)
        that are used by all client managers. Subclasses can override this method
        if they need to add additional client-specific fields.

        Args:
            server_config: ServerConfig object

        Returns:
            Dict containing client-specific configuration with core fields
        """
        # Base result containing only essential execution information
        result = {
            "command": server_config.command,
            "args": server_config.args,
        }

        # Add filtered environment variables if present
        non_empty_env = server_config.get_filtered_env_vars(os.environ)
        if non_empty_env:
            result["env"] = non_empty_env

        return result

    @classmethod
    def from_client_format(cls, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert client format to ServerConfig

        This is a helper method used by subclasses to convert from client-specific format to ServerConfig.

        Args:
            server_name: Name of the server
            client_config: Client-specific configuration

        Returns:
            ServerConfig object
        """
        # Create a dictionary that ServerConfig.from_dict can work with
        server_data = {
            "name": server_name,
            "command": client_config.get("command", ""),
            "args": client_config.get("args", []),
        }

        # Add environment variables if present
        if "env" in client_config:
            server_data["env_vars"] = client_config["env"]

        return ServerConfig.from_dict(server_data)

    def list_servers(self) -> List[str]:
        """List all MCP servers in client config

        Returns:
            List of server names
        """
        return list(self.get_servers().keys())

    def remove_server(self, server_name: str) -> bool:
        """Remove an MCP server from client config

        Args:
            server_name: Name of the server to remove

        Returns:
            bool: Success or failure
        """
        servers = self.get_servers()

        # Check if the server exists
        if server_name not in servers:
            logger.warning(f"Server {server_name} not found in {self.display_name} config")
            return False

        # Load full config and remove the server
        config = self._load_config()
        del config["mcpServers"][server_name]

        return self._save_config(config)

    def get_client_info(self) -> Dict[str, str]:
        """Get information about this client

        Returns:
            Dict: Information about the client including display name, download URL, and config path
        """
        return {"name": self.display_name, "download_url": self.download_url, "config_file": self.config_path}

    def is_client_installed(self) -> bool:
        """Check if this client is installed

        Returns:
            bool: True if client is installed, False otherwise
        """
        # Default implementation checks if the config directory exists
        # Can be overridden by subclasses
        return os.path.isdir(os.path.dirname(self.config_path))
