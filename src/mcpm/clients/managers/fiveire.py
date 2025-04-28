import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Union

from pydantic import TypeAdapter

from mcpm.clients.base import JSONClientManager
from mcpm.schemas.server_config import ServerConfig, STDIOServerConfig

logger = logging.getLogger(__name__)


class FiveireManager(JSONClientManager):
    # Client information
    client_key = "5ire"
    display_name = "5ire"
    download_url = "https://5ire.app/"

    configure_key_name = "servers"

    def __init__(self, config_path=None):
        """Initialize the 5ire client manager

        Args:
            config_path: Optional path to the config file. If not provided, uses default path.
        """
        super().__init__()

        if config_path:
            self.config_path = config_path
        else:
            # Set config path based on detected platform
            if self._system == "Darwin":  # macOS
                self.config_path = os.path.expanduser("~/Library/Application Support/5ire/mcp.json")
            elif self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("APPDATA", ""), "5ire", "mcp.json")
            else:
                # Linux
                self.config_path = os.path.expanduser("~/.config/5ire/mcp.json")

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get an empty configuration structure for this client

        Returns:
            Dict containing the client configuration with at least {"servers": []}
        """
        return {self.configure_key_name: []}

    def _load_config(self) -> Dict[str, Any]:
        """Load client configuration file

        Returns:
            Dict containing the client configuration with at least {"servers": []}
        """
        # Create empty config with the correct structure
        empty_config = self._get_empty_config()

        if not os.path.exists(self.config_path):
            logger.warning(f"Client config file not found at: {self.config_path}")
            return empty_config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Ensure servers section exists
                if self.configure_key_name not in config:
                    config[self.configure_key_name] = []
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

    def get_servers(self) -> Dict[str, Any]:
        """Get all MCP servers configured for this client

        Returns:
            Dict of server configurations by name
        """
        config = self._load_config()
        servers = {}

        # Convert list of servers to dictionary by name
        for server in config.get(self.configure_key_name, []):
            if "name" in server:
                servers[server["name"]] = server

        return servers

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
        return servers[server_name]

    def add_server(self, server_config: Union[ServerConfig, Dict[str, Any]], name: Optional[str] = None) -> bool:
        """Add or update a server in the client config

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
            client_config["name"] = server_name  # Ensure name is in the config

        # Update config
        config = self._load_config()

        # Check if server already exists and update it
        server_exists = False
        for i, server in enumerate(config.get(self.configure_key_name, [])):
            if server.get("name") == server_name:
                config[self.configure_key_name][i] = client_config
                server_exists = True
                break

        # If server doesn't exist, add it
        if not server_exists:
            if self.configure_key_name not in config:
                config[self.configure_key_name] = []
            config[self.configure_key_name].append(client_config)

        return self._save_config(config)

    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert ServerConfig to client-specific format

        Args:
            server_config: ServerConfig object

        Returns:
            Dict containing client-specific configuration
        """

        if isinstance(server_config, STDIOServerConfig):
            result = {
                "command": server_config.command,
                "args": server_config.args,
            }

            # Add filtered environment variables if present
            non_empty_env = server_config.get_filtered_env_vars(os.environ)
            if non_empty_env:
                result["env"] = non_empty_env
        else:
            result = server_config.to_dict()

        # Base result containing essential information
        key_slug = re.sub(r"[^a-zA-Z0-9]", "", server_config.name)
        # If the key starts with a number, prepend an key prefix
        if key_slug and key_slug[0].isdigit():
            key_slug = f"key{key_slug}"

        result.update(
            {
                "key": key_slug,
                "isActive": True,
            }
        )

        return result

    @classmethod
    def from_client_format(cls, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert client format to ServerConfig

        Args:
            server_name: Name of the server
            client_config: Client-specific configuration

        Returns:
            ServerConfig object
        """
        server_data = {
            "name": server_name,
        }
        server_data.update(client_config)
        return TypeAdapter(ServerConfig).validate_python(server_data)

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
        config = self._load_config()

        # Find and remove the server
        server_found = False
        for i, server in enumerate(config.get(self.configure_key_name, [])):
            if server.get("name") == server_name:
                config[self.configure_key_name].pop(i)
                server_found = True
                break

        if not server_found:
            logger.warning(f"Server {server_name} not found in {self.display_name} config")
            return False

        return self._save_config(config)

    def disable_server(self, server_name: str) -> bool:
        """Temporarily disable a server by setting isActive to False

        Args:
            server_name: Name of the server to disable

        Returns:
            bool: Success or failure
        """
        config = self._load_config()

        # Find and disable the server
        server_found = False
        for i, server in enumerate(config.get(self.configure_key_name, [])):
            if server.get("name") == server_name:
                config[self.configure_key_name][i]["isActive"] = False
                server_found = True
                break

        if not server_found:
            logger.warning(f"Server {server_name} not found in {self.display_name} config")
            return False

        return self._save_config(config)

    def enable_server(self, server_name: str) -> bool:
        """Re-enable a previously disabled server by setting isActive to True

        Args:
            server_name: Name of the server to enable

        Returns:
            bool: Success or failure
        """
        config = self._load_config()

        # Find and enable the server
        server_found = False
        for i, server in enumerate(config.get(self.configure_key_name, [])):
            if server.get("name") == server_name:
                config[self.configure_key_name][i]["isActive"] = True
                server_found = True
                break

        if not server_found:
            logger.warning(f"Server {server_name} not found in {self.display_name} config")
            return False

        return self._save_config(config)

    def is_server_disabled(self, server_name: str) -> bool:
        """Check if a server is currently disabled

        Args:
            server_name: Name of the server to check

        Returns:
            bool: True if server is disabled, False otherwise
        """
        servers = self.get_servers()

        # Check if the server exists and is not active
        return server_name in servers and servers[server_name].get("isActive", True) is False
