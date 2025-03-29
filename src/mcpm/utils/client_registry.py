"""
Client registry for MCPM
Provides a central registry of MCP client managers
"""

import logging
from typing import Dict, List, Optional

from mcpm.clients.base import BaseClientManager
from mcpm.utils.config import ConfigManager

# Import all client managers
from mcpm.clients.claude_desktop import ClaudeDesktopManager
from mcpm.clients.windsurf import WindsurfManager
from mcpm.clients.cursor import CursorManager

logger = logging.getLogger(__name__)


class ClientRegistry:
    """
    Registry of all MCP client managers
    Provides access to client managers and their configurations
    """

    # Configuration manager for system-wide settings
    _config_manager = ConfigManager()

    # Dictionary mapping client keys to manager instances
    _CLIENT_MANAGERS = {
        "claude-desktop": ClaudeDesktopManager(),
        "windsurf": WindsurfManager(),
        "cursor": CursorManager(),
    }

    @classmethod
    def get_client_manager(cls, client_name: str) -> Optional[BaseClientManager]:
        """
        Get the client manager for a given client name

        Args:
            client_name: Name of the client

        Returns:
            BaseClientManager: Client manager instance or None if not found
        """
        return cls._CLIENT_MANAGERS.get(client_name)

    @classmethod
    def get_all_client_managers(cls) -> Dict[str, BaseClientManager]:
        """
        Get all client managers

        Returns:
            Dict[str, BaseClientManager]: Dictionary mapping client names to manager instances
        """
        return cls._CLIENT_MANAGERS

    @classmethod
    def detect_installed_clients(cls) -> Dict[str, bool]:
        """
        Detect which MCP-compatible clients are installed on the system

        Returns:
            Dict[str, bool]: Dictionary mapping client names to installed status
        """
        return {client_name: manager.is_client_installed() for client_name, manager in cls._CLIENT_MANAGERS.items()}

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
        return {client_name: manager.get_client_info() for client_name, manager in cls._CLIENT_MANAGERS.items()}

    @classmethod
    def get_active_client(cls) -> str:
        """
        Get the active client name from the config manager

        Returns:
            str: Name of the active client
        """
        return cls._config_manager.get_active_client()

    @classmethod
    def set_active_client(cls, client_name: str) -> bool:
        """
        Set the active client in the config manager

        Args:
            client_name: Name of the client

        Returns:
            bool: Success or failure
        """
        return cls._config_manager.set_active_client(client_name)

    @classmethod
    def get_active_client_manager(cls) -> Optional[BaseClientManager]:
        """
        Get the client manager for the active client

        Returns:
            BaseClientManager: Client manager instance for the active client, or None if not found
        """
        active_client = cls.get_active_client()
        if not active_client:
            return None

        return cls.get_client_manager(active_client)

    @classmethod
    def get_recommended_client(cls) -> str:
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
