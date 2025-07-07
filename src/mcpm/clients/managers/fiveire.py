import logging
import os
import re
from typing import Any, Dict, Optional

from pydantic import TypeAdapter

from mcpm.clients.base import JSONClientManager
from mcpm.core.schema import ServerConfig, STDIOServerConfig

logger = logging.getLogger(__name__)


class FiveireManager(JSONClientManager):
    # Client information
    client_key = "5ire"
    display_name = "5ire"
    download_url = "https://5ire.app/"

    def __init__(self, config_path_override: Optional[str] = None):
        """Initialize the 5ire client manager

        Args:
            config_path_override: Optional path to override the default config file location
        """
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Set config path based on detected platform
            if self._system == "Darwin":  # macOS
                self.config_path = os.path.expanduser("~/Library/Application Support/5ire/mcp.json")
            elif self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("APPDATA", ""), "5ire", "mcp.json")
            else:
                # Linux
                self.config_path = os.path.expanduser("~/.config/5ire/mcp.json")

        self.server_name_key = {}

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get an empty configuration structure for this client

        Returns:
            Dict containing the client configuration with at least {"servers": []}
        """
        return {"mcpServers": {}}

    def _update_server_name_key(self):
        self.server_name_key = {}
        servers = self.get_servers()
        for key, server_config in servers.items():
            self.server_name_key[server_config.get("name", key)] = key

    def get_server(self, server_name: str) -> Optional[ServerConfig]:
        self._update_server_name_key()
        key = self.server_name_key.get(server_name)
        if key:
            return super().get_server(key)
        return None

    def remove_server(self, server_name: str) -> bool:
        self._update_server_name_key()
        key = self.server_name_key.get(server_name)
        if key:
            return super().remove_server(key)
        return False

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
            result["type"] = "local"
        else:
            result = server_config.to_dict()
            result["type"] = "remote"

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

    def disable_server(self, server_name: str) -> bool:
        """Temporarily disable a server by setting isActive to False

        Args:
            server_name: Name of the server to disable

        Returns:
            bool: Success or failure
        """
        config = self._load_config()

        if "mcpServers" not in config or server_name not in config["mcpServers"]:
            logger.warning(f"Server '{server_name}' not found in active servers")
            return False

        config["mcpServers"][server_name]["isActive"] = False

        return self._save_config(config)

    def enable_server(self, server_name: str) -> bool:
        """Re-enable a previously disabled server by setting isActive to True

        Args:
            server_name: Name of the server to enable

        Returns:
            bool: Success or failure
        """
        config = self._load_config()

        if "mcpServers" not in config or server_name not in config["mcpServers"]:
            logger.warning(f"Server '{server_name}' not found in active servers")
            return False

        config["mcpServers"][server_name]["isActive"] = True

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
