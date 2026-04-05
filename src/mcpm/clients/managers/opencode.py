"""
OpenCode integration for MCP
https://opencode.ai
"""

import json
import logging
import os
import re
import shutil
from typing import Any, Dict, List, Optional

from mcpm.clients.base import JSONClientManager
from mcpm.core.schema import CustomServerConfig, RemoteServerConfig, ServerConfig, STDIOServerConfig

logger = logging.getLogger(__name__)


class OpenCodeManager(JSONClientManager):
    """Manages OpenCode MCP server configurations.

    OpenCode uses a top-level "mcp" key (not "mcpServers") and a different
    server entry schema:
      - local:  { type, command (array), environment, enabled, timeout }
      - remote: { type, url, headers, oauth, enabled, timeout }
    """

    client_key = "opencode"
    display_name = "OpenCode"
    download_url = "https://opencode.ai"
    configure_key_name = "mcp"

    def __init__(self, config_path_override: Optional[str] = None):
        super().__init__(config_path_override=config_path_override)

        if config_path_override:
            self.config_path = config_path_override
        else:
            # OpenCode global config — XDG-style on all platforms
            self.config_path = os.path.expanduser("~/.config/opencode/opencode.json")

    def _get_empty_config(self) -> Dict[str, Any]:
        """Minimal valid OpenCode config skeleton."""
        return {
            "$schema": "https://opencode.ai/config.json",
            "mcp": {},
        }

    def _load_config(self) -> Dict[str, Any]:
        """Load config, stripping JSONC single-line comments before parsing.

        OpenCode officially supports JSONC (JSON with Comments). The base
        JSONClientManager uses json.load() which rejects comments, so we
        strip them first to avoid backing up a perfectly valid config.
        """
        empty_config = {self.configure_key_name: {}}

        if not os.path.exists(self.config_path):
            logger.debug(f"Client config file not found at: {self.config_path}")
            return empty_config

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw = f.read()
            # Strip // line comments that are NOT inside strings (e.g. URLs with ://)
            stripped = re.sub(r"(?m)^\s*//.*$", "", raw)  # full-line comments
            stripped = re.sub(r",(\s*[}\]])", r"\1", stripped)  # trailing commas
            config = json.loads(stripped)
            if self.configure_key_name not in config:
                config[self.configure_key_name] = {}
            return config
        except json.JSONDecodeError:
            logger.error(f"Error parsing OpenCode config: {self.config_path}")
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.bak"
                try:
                    os.rename(self.config_path, backup_path)
                    logger.info(f"Backed up corrupt config file to: {backup_path}")
                except Exception as e:
                    logger.error(f"Failed to backup corrupt file: {str(e)}")
            return empty_config

    # ------------------------------------------------------------------
    # Format translation
    # ------------------------------------------------------------------

    def to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert mcpm ServerConfig to OpenCode mcp entry format."""
        if isinstance(server_config, STDIOServerConfig):
            command_array: List[str] = [server_config.command]
            if server_config.args:
                command_array.extend(server_config.args)

            entry: Dict[str, Any] = {
                "type": "local",
                "command": command_array,
            }

            env = server_config.get_filtered_env_vars(os.environ)
            if env:
                entry["environment"] = env

        elif isinstance(server_config, RemoteServerConfig):
            entry = {
                "type": "remote",
                "url": server_config.url,
            }
            if server_config.headers:
                entry["headers"] = server_config.headers

        else:
            if isinstance(server_config, CustomServerConfig):
                entry = server_config.config
            else:
                entry = server_config.to_dict()

        return entry

    @classmethod
    def from_client_format(cls, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert OpenCode mcp entry to mcpm ServerConfig."""
        server_type = client_config.get("type", "local")

        if server_type == "remote":
            return RemoteServerConfig(
                name=server_name,
                url=client_config.get("url", ""),
                headers=client_config.get("headers", {}),
            )

        # Local server: split command array into command + args
        raw_command: List[str] = client_config.get("command", [])
        command = raw_command[0] if raw_command else ""
        args = raw_command[1:] if len(raw_command) > 1 else []

        # OpenCode uses "environment"; fall back to "env" for resilience
        env = client_config.get("environment") or client_config.get("env") or {}

        return STDIOServerConfig(
            name=server_name,
            command=command,
            args=args,
            env=env,
        )

    # ------------------------------------------------------------------
    # Client detection
    # ------------------------------------------------------------------

    def is_client_installed(self) -> bool:
        """Return True if the opencode binary is on PATH."""
        return shutil.which("opencode") is not None

    def get_client_info(self) -> Dict[str, str]:
        return {
            "name": self.display_name,
            "download_url": self.download_url,
            "config_file": self.config_path,
            "description": "OpenCode — AI coding agent CLI",
        }
