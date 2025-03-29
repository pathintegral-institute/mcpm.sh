"""
Windsurf integration utilities for MCP
"""

import os
import logging
import platform
from typing import Dict, Any, Union, Optional

from mcpm.utils.server_config import ServerConfig

from mcpm.clients.base import BaseClientManager

logger = logging.getLogger(__name__)


class WindsurfManager(BaseClientManager):
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
            if self._system == "Darwin":  # macOS
                self.config_path = os.path.expanduser("~/.codeium/windsurf/mcp_config.json")
            elif self._system == "Windows":
                self.config_path = os.path.join(
                    os.environ.get("LOCALAPPDATA", ""), "Codeium", "windsurf", "mcp_config.json"
                )
            else:
                # Linux
                self.config_path = os.path.expanduser("~/.codeium/windsurf/mcp_config.json")
