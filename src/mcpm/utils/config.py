"""
Configuration utilities for MCPM
"""

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Default configuration paths
DEFAULT_CONFIG_DIR = os.path.expanduser("~/.config/mcpm")
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_DIR, "config.json")
DEFAULT_AUTH_FILE = os.path.join(DEFAULT_CONFIG_DIR, "auth.json")
# Default port for HTTP mode
DEFAULT_PORT = 6276  # 6276 represents MCPM on a T9 keypad (6=M, 2=C, 7=P, 6=M)
# Default share address
DEFAULT_SHARE_ADDRESS = f"share.mcpm.sh:{DEFAULT_PORT}"

NODE_EXECUTABLES = ["npx", "bunx", "pnpm dlx", "yarn dlx"]


class ConfigManager:
    """Manages MCP basic configuration

    Note: This class only manages basic system configuration.
    Client-specific configurations are managed by ClientConfigManager.
    """

    def __init__(self, config_path: str = DEFAULT_CONFIG_FILE, auth_path: str = DEFAULT_AUTH_FILE):
        self.config_path = config_path
        self.auth_path = auth_path
        self.config_dir = os.path.dirname(config_path)
        self._config = {}
        self._auth_config = {}
        self._ensure_dirs()
        self._load_config()
        self._load_auth_config()

    def _ensure_dirs(self) -> None:
        """Ensure all configuration directories exist"""
        os.makedirs(self.config_dir, exist_ok=True)

    def _load_config(self) -> None:
        """Load configuration from file or create default"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._config = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Error parsing config file: {self.config_path}")
                self._config = self._default_config()
        else:
            self._config = self._default_config()
            self._save_config()

    def _load_auth_config(self) -> None:
        """Load auth configuration from file or create default"""
        if os.path.exists(self.auth_path):
            try:
                with open(self.auth_path, "r", encoding="utf-8") as f:
                    self._auth_config = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Error parsing auth file: {self.auth_path}")
                self._auth_config = {}
        else:
            self._auth_config = {}
            self._save_auth_config()

    def _default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        # Return empty config - don't set any defaults
        return {}

    def _save_config(self) -> None:
        """Save current configuration to file"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, indent=2)

    def _save_auth_config(self) -> None:
        """Save current auth configuration to file"""
        with open(self.auth_path, "w", encoding="utf-8") as f:
            json.dump(self._auth_config, f, indent=2)

    def get_config(self) -> Dict[str, Any]:
        """Get the complete configuration"""
        return self._config

    def get_auth_config(self) -> Dict[str, Any]:
        """Get the auth configuration"""
        return self._auth_config

    def set_config(self, key: str, value: Any) -> bool:
        """Set a configuration value and persist to file

        Args:
            key: Configuration key to set
            value: Value to set for the key (must be JSON serializable)

        Returns:
            bool: Success or failure
        """
        try:
            if value is None and key in self._config:
                # Remove the key if value is None
                del self._config[key]
            else:
                # Set the key to the provided value
                self._config[key] = value

            # Save the updated configuration
            self._save_config()
            return True
        except Exception as e:
            logger.error(f"Error setting configuration {key}: {str(e)}")
            return False

    def save_auth_config(self, api_key: str) -> bool:
        """Save the auth configuration"""
        self._auth_config["api_key"] = api_key
        self._save_auth_config()
        return True
