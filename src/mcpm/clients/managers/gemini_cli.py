"""
Gemini CLI integration utilities for MCP
"""

import logging
import os
import shutil
from typing import Any, Dict

from mcpm.clients.base import JSONClientManager

logger = logging.getLogger(__name__)


class GeminiCliManager(JSONClientManager):
    """Manages Gemini CLI MCP server configurations"""

    # Client information
    client_key = "gemini-cli"
    display_name = "Gemini CLI"
    download_url = "https://github.com/google-gemini/gemini-cli"

    def __init__(self, config_path_override: str | None = None):
        """Initialize the Gemini CLI client manager

        Args:
            config_path_override: Optional path to override the default config file location
        """
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Gemini CLI stores its settings in ~/.gemini/settings.json
            self.config_path = os.path.expanduser("~/.gemini/settings.json")

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Gemini CLI"""
        return {
            "mcpServers": {},
            # Include other default settings that Gemini CLI expects
            "contextFileName": "GEMINI.md",
            "autoAccept": False,
            "theme": "Default"
        }

    def is_client_installed(self) -> bool:
        """Check if Gemini CLI is installed
        Returns:
            bool: True if gemini command is available, False otherwise
        """
        gemini_executable = "gemini.exe" if self._system == "Windows" else "gemini"
        return shutil.which(gemini_executable) is not None

    def get_client_info(self) -> Dict[str, str]:
        """Get information about this client

        Returns:
            Dict: Information about the client including display name, download URL, and config path
        """
        return {
            "name": self.display_name,
            "download_url": self.download_url,
            "config_file": self.config_path,
            "description": "Google's Gemini CLI tool",
        }
