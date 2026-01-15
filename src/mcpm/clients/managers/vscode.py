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

    def __init__(self, config_path_override: str | None = None):
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # Set config path based on detected platform
            if self._system == "Windows":
                self.config_path = os.path.join(os.environ.get("APPDATA", ""), "Code", "User", "mcp.json")
            elif self._system == "Darwin":
                self.config_path = os.path.expanduser("~/Library/Application Support/Code/User/mcp.json")
            else:
                # Linux
                self.config_path = os.path.expanduser("~/.config/Code/User/mcp.json")

    def _load_config(self) -> Dict[str, Any]:
        """Load client configuration file

        {
            "servers": {
                "server_name": {
                    ...
                }
            },
            "inputs": []
        }

        Returns:
            Dict containing the client configuration with at least {"servers": {}, "inputs": []}
        """
        # Create empty config with the correct structure
        empty_config = {self.configure_key_name: {}, "inputs": []}

        if not os.path.exists(self.config_path):
            logger.warning(f"Client config file not found at: {self.config_path}")
            return empty_config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Ensure servers section exists
                if self.configure_key_name not in config:
                    config[self.configure_key_name] = {}
                # Ensure inputs array exists
                if "inputs" not in config:
                    config["inputs"] = []
                return config
        except json.JSONDecodeError:
            logger.error(f"Error parsing client config file: {self.config_path}")

        return empty_config

    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to client config file

        Args:
            config: Configuration to save (should include "servers" and optionally "inputs")

        Returns:
            bool: Success or failure
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

            # Ensure inputs array exists if not present
            if "inputs" not in config:
                config["inputs"] = []

            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving client config: {str(e)}")
            traceback.print_exc()
            return False

    def to_client_format(self, server_config) -> dict:
        """Convert ServerConfig to VSCode-specific format

        VSCode expects a "type" field in addition to command and args.
        """
        from mcpm.core.schema import STDIOServerConfig

        if isinstance(server_config, STDIOServerConfig):
            result = {
                "type": "stdio",
                "command": server_config.command,
                "args": server_config.args,
            }

            # Add environment variables if present
            import os

            non_empty_env = server_config.get_filtered_env_vars(os.environ)
            if non_empty_env:
                result["env"] = non_empty_env

            return result
        else:
            # For other server types, use the default implementation
            return super().to_client_format(server_config)
