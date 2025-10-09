"""
Qwen CLI integration utilities for MCP
"""

import logging
import os
import shutil
from typing import Any, Dict

from mcpm.clients.base import JSONClientManager

logger = logging.getLogger(__name__)


class QwenCliManager(JSONClientManager):
    """Manages Qwen CLI MCP server configurations"""

    # Client information
    client_key = "qwen-cli"
    display_name = "Qwen CLI"
    download_url = "https://github.com/QwenLM/qwen-code"

    def __init__(self, config_path_override: str | None = None):
        """Initialize the Qwen CLI client manager

        Args:
            config_path_override: Optional path to override the default config file location
        """
        # Qwen CLI stores its settings in ~/.qwen/settings.json
        self.config_path = os.path.expanduser("~/.qwen/settings.json")
        super().__init__(config_path_override=config_path_override)

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Qwen CLI"""
        return {
            "mcpServers": {},
            # Include other default settings that Qwen CLI expects
            "theme": "Qwen Dark",
            "selectedAuthType": "openai",
        }

    def is_client_installed(self) -> bool:
        """Check if Qwen CLI is installed
        Returns:
            bool: True if qwen command is available, False otherwise
        """
        qwen_executable = "qwen.exe" if self._system == "Windows" else "qwen"
        return shutil.which(qwen_executable) is not None

    def get_client_info(self) -> Dict[str, str]:
        """Get information about this client

        Returns:
            Dict: Information about the client including display name, download URL, and config path
        """
        return {
            "name": self.display_name,
            "download_url": self.download_url,
            "config_file": self.config_path,
            "description": "Alibaba's Qwen CLI tool",
        }
