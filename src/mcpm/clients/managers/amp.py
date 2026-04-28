"""
Sourcegraph Amp integration utilities for MCP
"""

import logging
import os
import shutil
from typing import Any, Dict

from mcpm.clients.base import JSONClientManager

logger = logging.getLogger(__name__)


class AmpManager(JSONClientManager):
    """Manages Sourcegraph Amp MCP server configurations"""

    # Client information
    client_key = "amp"
    display_name = "Sourcegraph Amp"
    download_url = "https://ampcode.com"
    # Amp groups its settings under flat dotted keys (amp.theme,
    # amp.modelOverrides, amp.mcpServers, etc.) rather than nesting them
    # under a top-level "amp" object. Python's dict access handles the
    # dot in the key name without special-casing — `config["amp.mcpServers"]`
    # works the same as `config["servers"]` for VSCode.
    configure_key_name = "amp.mcpServers"

    def __init__(self, config_path_override: str | None = None):
        """Initialize the Sourcegraph Amp client manager

        Args:
            config_path_override: Optional path to override the default config file location
        """
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Amp stores its settings in ~/.config/amp/settings.json on
            # macOS, Linux, and Windows (per Amp's docs at
            # https://ampcode.com/manual).
            self.config_path = os.path.expanduser("~/.config/amp/settings.json")

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Sourcegraph Amp"""
        return {self.configure_key_name: {}}

    def is_client_installed(self) -> bool:
        """Check if Sourcegraph Amp is installed
        Returns:
            bool: True if amp command is available, False otherwise
        """
        # shutil.which() handles Windows PATHEXT automatically (.cmd, .bat, .exe, etc.)
        return shutil.which("amp") is not None

    def get_client_info(self) -> Dict[str, str]:
        """Get information about this client

        Returns:
            Dict: Information about the client including display name, download URL, and config path
        """
        return {
            "name": self.display_name,
            "download_url": self.download_url,
            "config_file": self.config_path,
            "description": "Sourcegraph's Amp coding agent CLI",
        }
