"""
Claude Code CLI integration utilities for MCP
"""

import logging
import os
import shutil
from typing import Any, Dict

from mcpm.clients.base import JSONClientManager

logger = logging.getLogger(__name__)


class ClaudeCodeManager(JSONClientManager):
    """Manages Claude Code CLI MCP server configurations"""

    # Client information
    client_key = "claude-code"
    display_name = "Claude Code"
    download_url = "https://docs.anthropic.com/en/docs/claude-code"

    def __init__(self, config_path=None):
        """Initialize the Claude Code client manager

        Args:
            config_path: Optional path to the config file. If not provided, uses default path.
        """
        super().__init__()

        if config_path:
            self.config_path = config_path
        else:
            self.config_path = os.path.expanduser("~/.claude.json")

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Claude Code"""
        return {"mcpServers": {}}

    def is_client_installed(self) -> bool:
        """Check if Claude Code CLI is installed
        Returns:
            bool: True if claude command is available, False otherwise
        """
        claude_executable = "claude.exe" if self._system == "Windows" else "claude"
        return shutil.which(claude_executable) is not None

    def get_client_info(self) -> Dict[str, str]:
        """Get information about this client

        Returns:
            Dict: Information about the client including display name, download URL, and config path
        """
        return {
            "name": self.display_name,
            "download_url": self.download_url,
            "config_file": self.config_path,
            "description": "Anthropic's Claude Code CLI tool"
        }
