"""
Kiro IDE integration utilities for MCP
"""

import logging
import os
import shutil
from typing import Any, Dict

from mcpm.clients.base import JSONClientManager

logger = logging.getLogger(__name__)


class KiroManager(JSONClientManager):
    """Manages Kiro IDE MCP server configurations"""

    # Client information
    client_key = "kiro"
    display_name = "Kiro"
    download_url = "https://kiro.dev"

    def __init__(self, config_path_override: str | None = None):
        """Initialize the Kiro client manager

        Args:
            config_path_override: Optional path to override the default config file location
        """
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Kiro stores its MCP settings in ~/.kiro/settings/mcp.json
            # across macOS, Linux, and Windows (per Kiro's docs at
            # https://kiro.dev/docs/mcp).
            self.config_path = os.path.expanduser("~/.kiro/settings/mcp.json")

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Kiro"""
        return {self.configure_key_name: {}}

    def is_client_installed(self) -> bool:
        """Check if Kiro is installed
        Returns:
            bool: True if kiro command is available, False otherwise
        """
        # shutil.which() handles Windows PATHEXT automatically (.cmd, .bat, .exe, etc.)
        return shutil.which("kiro") is not None

    def get_client_info(self) -> Dict[str, str]:
        """Get information about this client

        Returns:
            Dict: Information about the client including display name, download URL, and config path
        """
        return {
            "name": self.display_name,
            "download_url": self.download_url,
            "config_file": self.config_path,
            "description": "Kiro coding agent IDE",
        }
