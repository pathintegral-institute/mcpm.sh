"""
Windsurf integration utilities for MCP
"""

import logging
import os
from typing import Any, Dict

from mcpm.clients.base import JSONClientManager
from mcpm.core.schema import ServerConfig, STDIOServerConfig

logger = logging.getLogger(__name__)


class WindsurfManager(JSONClientManager):
    """Manages Windsurf MCP server configurations"""

    # Client information
    client_key = "windsurf"
    display_name = "Windsurf"
    download_url = "https://codeium.com/windsurf/download"

    def __init__(self, config_path=None):
        """Initialize the Windsurf client manager

        Args:
            config_path: Optional path to the config file. If not provided, uses default path.
        """
        super().__init__()

        if config_path:
            self.config_path = config_path
        else:
            # Set config path based on detected platform
            if self._system == "Windows":
                self.config_path = os.path.join(
                    os.environ.get("USERPROFILE", ""), ".codeium", "windsurf", "mcp_config.json"
                )
            else:
                # MacOS or Linux
                self.config_path = os.path.expanduser("~/.codeium/windsurf/mcp_config.json")

    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        if isinstance(server_config, STDIOServerConfig):
            return super().to_client_format(server_config)
        else:
            result = server_config.to_dict()
            result["serverUrl"] = result.pop("url")
            return result

    def from_client_format(self, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        if "serverUrl" in client_config:
            client_config["url"] = client_config.pop("serverUrl")
        return super().from_client_format(server_name, client_config)
