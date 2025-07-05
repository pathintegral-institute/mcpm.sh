"""
Continue MCP server configuration manager
"""

import logging
import os
from typing import Any, Dict, List, Optional

from pydantic import TypeAdapter

from mcpm.clients.base import YAMLClientManager
from mcpm.core.schema import ServerConfig, STDIOServerConfig

logger = logging.getLogger(__name__)


class ContinueManager(YAMLClientManager):
    """Manages Continue MCP server configurations

    Continue uses YAML files for configuration instead of JSON, and has a different
    structure compared to other clients. This manager handles the Continue-specific
    configuration format and file locations.
    """

    # Client information
    client_key = "continue"
    display_name = "Continue"
    download_url = "https://marketplace.visualstudio.com/items?itemName=Continue.continue"

    def __init__(self, config_path_override: Optional[str] = None):
        """Initialize the Continue client manager

        Args:
            config_path_override: Optional path to override the default config file location
        """
        super().__init__(config_path_override=config_path_override)
        # Customize YAML handler
        self.yaml_handler.indent(mapping=2, sequence=4, offset=2)
        self.yaml_handler.preserve_quotes = True

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Set config path based on detected platform
            if self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("USERPROFILE", ""), ".continue", "config.yaml")
            else:
                # MacOS or Linux
                self.config_path = os.path.expanduser("~/.continue/config.yaml")

            # Also check for workspace config
            workspace_config = os.path.join(os.getcwd(), ".continue", "config.yaml")
            if os.path.exists(workspace_config):
                # Prefer workspace config if it exists
                self.config_path = workspace_config

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get an empty configuration structure for Continue

        Returns:
            Dict containing the empty configuration structure
        """
        return {
            "name": "Local Assistant",
            "version": "1.0.0",
            "schema": "v1",
            "models": [],
            "rules": [],
            "prompts": [],
            "context": [],
            "mcpServers": [],
            "data": [],
        }

    def _get_servers_section(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get the section of the config that contains server definitions

        Args:
            config: The loaded configuration

        Returns:
            The section containing server definitions
        """
        return config.get("mcpServers", [])

    def _get_server_config(self, config: Dict[str, Any], server_name: str) -> Optional[Dict[str, Any]]:
        """Get a server configuration from the config by name

        Args:
            config: The loaded configuration
            server_name: Name of the server to find

        Returns:
            Server configuration if found, None otherwise
        """
        for server in self._get_servers_section(config):
            if server.get("name") == server_name:
                return server
        return None

    def _get_all_server_names(self, config: Dict[str, Any]) -> List[str]:
        """Get all server names from the configuration

        Args:
            config: The loaded configuration

        Returns:
            List of server names
        """
        return [server.get("name") for server in self._get_servers_section(config) if server.get("name") is not None]  # type: ignore

    def _add_server_to_config(
        self, config: Dict[str, Any], server_name: str, server_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add or update a server in the config

        Args:
            config: The loaded configuration
            server_name: Name of the server to add or update
            server_config: Server configuration to add or update

        Returns:
            Updated configuration
        """
        # Ensure server_config has a name field for YAML list format
        if "name" not in server_config:
            server_config["name"] = server_name

        # Find and update existing server or add new one
        server_found = False
        for i, server in enumerate(self._get_servers_section(config)):
            if server.get("name") == server_name:
                # Update existing server while preserving any extra fields
                # that might be present in the original config
                for key, value in server_config.items():
                    config["mcpServers"][i][key] = value
                server_found = True
                break

        if not server_found:
            if "mcpServers" not in config:
                config["mcpServers"] = []
            config["mcpServers"].append(server_config)

        return config

    def _remove_server_from_config(self, config: Dict[str, Any], server_name: str) -> Dict[str, Any]:
        """Remove a server from the config

        Args:
            config: The loaded configuration
            server_name: Name of the server to remove

        Returns:
            Updated configuration
        """
        for i, server in enumerate(self._get_servers_section(config)):
            if server.get("name") == server_name:
                # Remove the server
                config["mcpServers"].pop(i)
                break
        return config

    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert ServerConfig to Continue-specific format

        Args:
            server_config: ServerConfig object

        Returns:
            Dict containing client-specific configuration
        """
        # Base result containing only essential execution information
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

        return result

    def from_client_format(self, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert Continue format to ServerConfig

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
