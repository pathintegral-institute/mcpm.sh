import json
import logging
import os
import traceback
from typing import Any, Dict

from mcpm.clients.base import JSONClientManager

logger = logging.getLogger(__name__)


class VSCodeManager(JSONClientManager):
    """Manages VSCode MCP server configurations"""

    # Client information
    client_key = "vscode"
    display_name = "VSCode"
    download_url = "https://code.visualstudio.com/"
    configure_key_name = "servers"

    def __init__(self, config_path=None):
        super().__init__()

        if config_path:
            self.config_path = config_path
        else:
            # Set config path based on detected platform
            if self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("APPDATA", ""), "Code", "User", "settings.json")
            elif self._system == "Darwin":
                self.config_path = os.path.expanduser("~/Library/Application Support/Code/User/settings.json")
            else:
                # MacOS or Linux
                self.config_path = os.path.expanduser("~/.config/Code/User/settings.json")

    def _load_config(self) -> Dict[str, Any]:
        """Load client configuration file

        {
            "mcp": {
                "servers": {
                    "server_name": {
                        ...
                    }
                }
            }
        }

        Returns:
            Dict containing the client configuration with at least {"mcpServers": {}}
        """
        # Create empty config with the correct structure
        empty_config = {"mcp": {self.configure_key_name: {}}}

        if not os.path.exists(self.config_path):
            logger.warning(f"Client config file not found at: {self.config_path}")
            return empty_config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                if "mcp" not in config:
                    config["mcp"] = {}
                # Ensure mcpServers section exists
                if self.configure_key_name not in config["mcp"]:
                    config["mcp"][self.configure_key_name] = {}
                return config["mcp"]
        except json.JSONDecodeError:
            logger.error(f"Error parsing client config file: {self.config_path}")

        # Vscode config includes other information, so we makes no change on it
        return empty_config

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
            if not os.path.exists(self.config_path):
                current_config = {}
            else:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    current_config = json.load(f)
            current_config["mcp"] = config
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(current_config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving client config: {str(e)}")
            traceback.print_exc()
            return False
