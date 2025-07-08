"""
Client registry for MCPM
Provides a central registry of MCP client managers
"""

import logging
from typing import Dict, List, Optional

from mcpm.clients.base import BaseClientManager
from mcpm.clients.client_config import ClientConfigManager

# Import all client managers
from mcpm.clients.managers.claude_code import ClaudeCodeManager
from mcpm.clients.managers.claude_desktop import ClaudeDesktopManager
from mcpm.clients.managers.cline import ClineManager, RooCodeManager
from mcpm.clients.managers.codex_cli import CodexCliManager
from mcpm.clients.managers.continue_extension import ContinueManager
from mcpm.clients.managers.cursor import CursorManager
from mcpm.clients.managers.fiveire import FiveireManager
from mcpm.clients.managers.gemini_cli import GeminiCliManager
from mcpm.clients.managers.goose import GooseClientManager
from mcpm.clients.managers.trae import TraeManager
from mcpm.clients.managers.vscode import VSCodeManager
from mcpm.clients.managers.windsurf import WindsurfManager

logger = logging.getLogger(__name__)


class ClientRegistry:
    """
    Registry of all MCP client managers
    Provides access to client managers and their configurations
    """

    # Client configuration manager for system-wide client settings
    _client_config_manager = ClientConfigManager()

    # Dictionary mapping client keys to manager classes
    _CLIENT_MANAGERS = {
        "claude-code": ClaudeCodeManager,
        "claude-desktop": ClaudeDesktopManager,
        "windsurf": WindsurfManager,
        "cursor": CursorManager,
        "cline": ClineManager,
        "continue": ContinueManager,
        "goose-cli": GooseClientManager,
        "5ire": FiveireManager,
        "roo-code": RooCodeManager,
        "trae": TraeManager,
        "vscode": VSCodeManager,
        "gemini-cli": GeminiCliManager,
        "codex-cli": CodexCliManager,
    }

    @classmethod
    def get_client_manager(
        cls, client_name: str, config_path_override: Optional[str] = None
    ) -> Optional[BaseClientManager]:
        """
        Get the client manager for a given client name

        Args:
            client_name: Name of the client
            config_path_override: Optional path to override the default config file location

        Returns:
            BaseClientManager: Client manager instance or None if not found
        """
        manager_class = cls._CLIENT_MANAGERS.get(client_name)
        if manager_class:
            return manager_class(config_path_override=config_path_override)
        return None

    @classmethod
    def get_all_client_managers(cls) -> Dict[str, BaseClientManager]:
        """
        Get all client managers

        Returns:
            Dict[str, BaseClientManager]: Dictionary mapping client names to manager instances
        """
        return {name: manager() for name, manager in cls._CLIENT_MANAGERS.items()}

    @classmethod
    def detect_installed_clients(cls) -> Dict[str, bool]:
        """
        Detect which MCP-compatible clients are installed on the system

        Returns:
            Dict[str, bool]: Dictionary mapping client names to installed status
        """
        return {client_name: manager().is_client_installed() for client_name, manager in cls._CLIENT_MANAGERS.items()}

    @classmethod
    def get_client_info(cls, client_name: str) -> Dict[str, str]:
        """
        Get client display information

        Args:
            client_name: Name of the client

        Returns:
            Dict containing display name, download URL, and config path
        """
        client_manager = cls.get_client_manager(client_name)
        if client_manager:
            return client_manager.get_client_info()
        return {}

    @classmethod
    def get_all_client_info(cls) -> Dict[str, Dict[str, str]]:
        """
        Get display information for all supported clients

        Returns:
            Dict[str, Dict[str, str]]: Dictionary mapping client names to display information
        """
        return {client_name: manager().get_client_info() for client_name, manager in cls._CLIENT_MANAGERS.items()}

    @classmethod
    def get_recommended_client(cls) -> str | None:
        """
        Get the recommended client based on installation status

        Returns:
            str: Name of the recommended client
        """
        clients = cls.detect_installed_clients()

        # Prioritize clients that are actually installed
        for client, installed in clients.items():
            if installed:
                return client

        # Return None if no clients are installed
        return None

    @classmethod
    def get_supported_clients(cls) -> List[str]:
        """
        Get a list of supported client names

        Returns:
            List[str]: List of supported client names
        """
        return list(cls._CLIENT_MANAGERS.keys())
