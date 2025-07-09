"""
Codex CLI integration utilities for MCP
"""

import logging
import os
import shutil
from typing import Any, Dict

import tomli
import tomli_w

from mcpm.clients.base import JSONClientManager

logger = logging.getLogger(__name__)


class CodexCliManager(JSONClientManager):
    """Manages Codex CLI MCP server configurations"""

    # Client information
    client_key = "codex-cli"
    display_name = "Codex CLI"
    download_url = "https://github.com/openai/codex"
    configure_key_name = "mcp_servers"  # Codex uses mcp_servers instead of mcpServers

    def __init__(self, config_path_override: str | None = None):
        """Initialize the Codex CLI client manager

        Args:
            config_path_override: Optional path to override the default config file location
        """
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Codex CLI stores its settings in ~/.codex/config.toml
            self.config_path = os.path.expanduser("~/.codex/config.toml")

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Codex CLI"""
        return {"mcp_servers": {}}

    def is_client_installed(self) -> bool:
        """Check if Codex CLI is installed
        Returns:
            bool: True if codex command is available, False otherwise
        """
        codex_executable = "codex.exe" if self._system == "Windows" else "codex"
        return shutil.which(codex_executable) is not None

    def get_client_info(self) -> Dict[str, str]:
        """Get information about this client

        Returns:
            Dict: Information about the client including display name, download URL, and config path
        """
        return {
            "name": self.display_name,
            "download_url": self.download_url,
            "config_file": self.config_path,
            "description": "OpenAI's Codex CLI tool",
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load client configuration file

        Returns:
            Dict containing the client configuration with at least {"mcp_servers": {}}
        """
        try:
            # Check if config file exists
            if not os.path.exists(self.config_path):
                # Create empty config
                return self._get_empty_config()

            # Codex uses TOML format instead of JSON
            with open(self.config_path, "rb") as f:
                config = tomli.load(f)

            # Ensure mcp_servers key exists
            if self.configure_key_name not in config:
                config[self.configure_key_name] = {}

            return config
        except Exception as e:
            logger.error(f"Error loading Codex config: {e}")
            return self._get_empty_config()

    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to client config file

        Args:
            config: Configuration to save

        Returns:
            bool: Success or failure
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            # Codex uses TOML format instead of JSON
            with open(self.config_path, "wb") as f:
                tomli_w.dump(config, f)
            return True
        except Exception as e:
            logger.error(f"Error saving Codex config: {e}")
            return False
