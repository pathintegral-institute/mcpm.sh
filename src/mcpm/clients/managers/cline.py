import logging
import os
from typing import Any, Dict

from mcpm.clients.base import JSONClientManager

logger = logging.getLogger(__name__)

class ClineManager(JSONClientManager):
    """Manages Cline MCP server configurations"""

    # Client information
    client_key = "cline"
    display_name = "Cline"
    download_url = "https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev"

    def __init__(self, config_path=None):
        """Initialize the Cline client manager

        Args:
            config_path: Optional path to the config file. If not provided, uses default path.
        """
        super().__init__()

        if config_path:
            self.config_path = config_path
        else:
            # Set config path based on detected platform
            if self._system == "Darwin":  # macOS
                self.config_path = os.path.expanduser("~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json")
            elif self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("APPDATA", ""), "Code", "User", "globalStorage", "saoudrizwan.claude-dev", "settings", "cline_mcp_settings.json")
            else:
                # Linux
                self.config_path = os.path.expanduser("~/.config/Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json")

    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Cline"""
        return {self.configure_key_name: {}}

    def disable_server(self, server_name: str) -> bool:
        """Temporarily disable a server by adding a 'disabled' field to its configuration

        Args:
            server_name: Name of the server to disable

        Returns:
            bool: Success or failure
        """
        config = self._load_config()

        # Check if the server exists in active servers
        if self.configure_key_name not in config or server_name not in config[self.configure_key_name]:
            logger.warning(f"Server '{server_name}' not found in active servers")
            return False

        # Add disabled field to the server config
        config[self.configure_key_name][server_name]["disabled"] = True

        return self._save_config(config)

    def enable_server(self, server_name: str) -> bool:
        """Re-enable a previously disabled server by removing the 'disabled' field

        Args:
            server_name: Name of the server to enable

        Returns:
            bool: Success or failure
        """
        config = self._load_config()

        # Check if the server exists
        if self.configure_key_name not in config or server_name not in config[self.configure_key_name]:
            logger.warning(f"Server '{server_name}' not found in configuration")
            return False

        # Check if the server is disabled
        if "disabled" not in config[self.configure_key_name][server_name]:
            logger.warning(f"Server '{server_name}' is not disabled")
            return True  # Already enabled, so technically success

        # Remove the disabled field
        del config[self.configure_key_name][server_name]["disabled"]

        return self._save_config(config)

    def is_server_disabled(self, server_name: str) -> bool:
        """Check if a server is currently disabled

        Args:
            server_name: Name of the server to check

        Returns:
            bool: True if server is disabled, False otherwise
        """
        config = self._load_config()

        # Check if the server exists and has the disabled field set to True
        return (
            self.configure_key_name in config
            and server_name in config[self.configure_key_name]
            and config[self.configure_key_name][server_name].get("disabled", False) is True
        )


class RooCodeManager(ClineManager):

    # Client information
    client_key = "roo-code"
    display_name = "Roo Code"
    download_url = "https://marketplace.visualstudio.com/items?itemName=RooVeterinaryInc.roo-cline"

    def __init__(self, config_path=None):
        """Initialize the Roo Code client manager

        Args:
            config_path: Optional path to the config file. If not provided, uses default path.
        """
        super().__init__()

        if config_path:
            self.config_path = config_path
        else:
            # Set config path based on detected platform
            if self._system == "Darwin":  # macOS
                self.config_path = os.path.expanduser("~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json")
            elif self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("APPDATA", ""), "Code", "User", "globalStorage", "rooveterinaryinc.roo-cline", "settings", "mcp_settings.json")
            else:
                # Linux
                self.config_path = os.path.expanduser("~/.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/mcp_settings.json")
