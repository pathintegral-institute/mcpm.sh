"""
Cursor integration utilities for MCP
"""

import os
import logging
import platform
from typing import Dict, Any

from mcpm.clients.base import BaseClientManager

logger = logging.getLogger(__name__)


class CursorManager(BaseClientManager):
    """Manages Cursor MCP server configurations"""

    # Client information
    client_key = "cursor"
    display_name = "Cursor"
    download_url = "https://cursor.sh/download"

    def __init__(self, config_path=None):
        """Initialize the Cursor client manager

        Args:
            config_path: Optional path to the config file. If not provided, uses default path.
        """
        super().__init__()

        if config_path:
            self.config_path = config_path
        else:
            # Set config path based on detected platform
            if self._system == "Darwin":  # macOS
                self.config_path = os.path.expanduser("~/Library/Application Support/Cursor/User/mcp_config.json")
            elif self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("APPDATA", ""), "Cursor", "User", "mcp_config.json")
            else:
                # Linux
                self.config_path = os.path.expanduser("~/.config/Cursor/User/mcp_config.json")

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Cursor"""
        return {"mcpServers": {}}
