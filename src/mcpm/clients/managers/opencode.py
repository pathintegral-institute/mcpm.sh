"""
OpenCode integration utilities for MCP
"""

import logging
import os
import shutil
from typing import Any, Dict

from mcpm.clients.base import JSONClientManager

logger = logging.getLogger(__name__)


class OpenCodeManager(JSONClientManager):
    """Manages OpenCode MCP server configurations.

    OpenCode is an open-source AI coding agent that runs as a CLI/TUI
    (https://github.com/sst/opencode). Its config file is JSON at
    `~/.config/opencode/opencode.json` and uses the top-level key `mcp`
    (not the typical `mcpServers`).
    """

    # Client information
    client_key = "opencode"
    display_name = "OpenCode"
    download_url = "https://github.com/sst/opencode"
    configure_key_name = "mcp"  # OpenCode uses `mcp` instead of `mcpServers`

    def __init__(self, config_path_override: str | None = None):
        """Initialize the OpenCode client manager

        Args:
            config_path_override: Optional path to override the default config file location
        """
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # OpenCode stores its settings in ~/.config/opencode/opencode.json
            self.config_path = os.path.expanduser("~/.config/opencode/opencode.json")

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for OpenCode"""
        return {self.configure_key_name: {}}

    def is_client_installed(self) -> bool:
        """Check if OpenCode is installed.

        Returns:
            bool: True if `opencode` binary is on PATH, False otherwise.
        """
        # shutil.which() handles Windows PATHEXT automatically (.cmd, .bat, .exe, etc.)
        return shutil.which("opencode") is not None

    def get_client_info(self) -> Dict[str, str]:
        """Get information about this client

        Returns:
            Dict: Information about the client including display name, download URL, and config path
        """
        return {
            "name": self.display_name,
            "download_url": self.download_url,
            "config_file": self.config_path,
            "description": "Open-source AI coding agent (CLI / TUI)",
        }
