"""
Goose MCP server configuration manager
"""

import logging
import os
from typing import Any, Dict, Optional

from pydantic import TypeAdapter

from mcpm.clients.base import YAMLClientManager
from mcpm.core.schema import CustomServerConfig, ServerConfig, STDIOServerConfig

logger = logging.getLogger(__name__)


class GooseClientManager(YAMLClientManager):
    """Manages Goose MCP server configurations

    Goose uses YAML files for configuration with a specific structure for extensions.
    This manager handles the Goose-specific configuration format and file locations.
    """

    # Client information
    client_key = "goose-cli"
    display_name = "Goose CLI"
    download_url = "https://github.com/block/goose/releases/download/stable/download_cli.sh"

    def __init__(self, config_path_override: Optional[str] = None):
        """Initialize the Goose CLI client manager

        Args:
            config_path_override: Optional path to override the default config file location
        """
        super().__init__(config_path_override=config_path_override)
        # Customize YAML handler
        self.yaml_handler.indent(mapping=2, sequence=0, offset=0)
        self.yaml_handler.preserve_quotes = True

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Set config path based on detected platform
            if self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("USERPROFILE", ""), ".config", "goose", "config.yaml")
            else:
                # MacOS or Linux
                self.config_path = os.path.expanduser("~/.config/goose/config.yaml")

            # Also check for workspace config
            workspace_config = os.path.join(os.getcwd(), ".goose", "config.yaml")
            if os.path.exists(workspace_config):
                # Prefer workspace config if it exists
                self.config_path = workspace_config

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get an empty configuration structure for Goose

        Returns:
            Dict containing the empty configuration structure
        """
        return {"extensions": {}}

    def _get_servers_section(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get the section of the config that contains server definitions

        Args:
            config: The loaded configuration

        Returns:
            The section containing server definitions
        """
        return config.get("extensions", {})

    def _get_server_config(self, config: Dict[str, Any], server_name: str) -> Optional[Dict[str, Any]]:
        """Get a server configuration from the config by name

        Args:
            config: The loaded configuration
            server_name: Name of the server to find

        Returns:
            Server configuration if found, None otherwise
        """
        return self._get_servers_section(config).get(server_name)

    def _get_all_server_names(self, config: Dict[str, Any]) -> list[str]:
        """Get all server names from the configuration

        Args:
            config: The loaded configuration

        Returns:
            List of server names
        """
        return list(self._get_servers_section(config).keys())

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
        if "extensions" not in config:
            config["extensions"] = {}

        config["extensions"][server_name] = server_config
        return config

    def _remove_server_from_config(self, config: Dict[str, Any], server_name: str) -> Dict[str, Any]:
        """Remove a server from the config

        Args:
            config: The loaded configuration
            server_name: Name of the server to remove

        Returns:
            Updated configuration
        """
        if "extensions" in config and server_name in config["extensions"]:
            del config["extensions"][server_name]
        return config

    def _normalize_server_config(self, server_config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize server configuration for external use

        This method transforms Goose-specific configuration formats to a standard format
        expected by external components.

        Args:
            server_config: Client-specific server configuration

        Returns:
            Normalized server configuration
        """
        # Create a copy
        normalized = dict(server_config)

        # Map Goose-specific fields to standard fields
        if normalized.get("type") == "builtin":
            return {"config": normalized}
        if "cmd" in normalized:
            normalized["command"] = normalized.pop("cmd")
        if "envs" in normalized:
            normalized["env"] = normalized.pop("envs")

        return normalized

    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert ServerConfig to Goose-specific format

        Args:
            server_config: ServerConfig object

        Returns:
            Dict containing client-specific configuration
        """
        # Base result containing only essential execution information
        if isinstance(server_config, STDIOServerConfig):
            result = {
                "cmd": server_config.command,
                "args": server_config.args,
                "type": "stdio",
            }

            # Add filtered environment variables if present
            non_empty_env = server_config.get_filtered_env_vars(os.environ)
            if non_empty_env:
                result["envs"] = non_empty_env
        elif isinstance(server_config, CustomServerConfig):
            result = dict(server_config.config)
            result["type"] = "builtin"
        else:
            result = server_config.to_dict()
            result["type"] = "sse"

        result.update(
            {
                "name": server_config.name,
                "enabled": True,
                "description": server_config.name,
            }
        )

        return result

    def from_client_format(self, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert Goose format to ServerConfig

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
