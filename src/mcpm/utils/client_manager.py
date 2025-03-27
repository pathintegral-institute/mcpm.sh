"""
Client manager utilities for MCPM
"""

from typing import Optional, Tuple

from mcpm.clients.claude_desktop import ClaudeDesktopManager
from mcpm.clients.windsurf import WindsurfManager
from mcpm.clients.cursor import CursorManager
from mcpm.clients.base import BaseClientManager
from mcpm.utils.config import ConfigManager

# Create client manager instances
claude_manager = ClaudeDesktopManager()
windsurf_manager = WindsurfManager()
cursor_manager = CursorManager()

# Create config manager instance
config_manager = ConfigManager()

# Client manager mapping
CLIENT_MANAGERS = {
    "claude-desktop": claude_manager,
    "windsurf": windsurf_manager,
    "cursor": cursor_manager
}

# Client display names
CLIENT_DISPLAY_NAMES = {
    "claude-desktop": "Claude Desktop",
    "windsurf": "Windsurf",
    "cursor": "Cursor"
}

# Client download URLs
CLIENT_URLS = {
    "claude-desktop": "https://claude.ai/download",
    "windsurf": "https://codeium.com/windsurf/download",
    "cursor": "https://cursor.sh/download"
}

def get_client_manager(client_name: str) -> Optional[BaseClientManager]:
    """
    Get the client manager for a given client name
    
    Args:
        client_name: Name of the client
        
    Returns:
        BaseClientManager: Client manager instance or None if not found
    """
    return CLIENT_MANAGERS.get(client_name)

def get_client_info(client_name: str) -> Tuple[Optional[BaseClientManager], str, str]:
    """
    Get client manager and related information
    
    Args:
        client_name: Name of the client
        
    Returns:
        Tuple containing:
            - BaseClientManager: Client manager instance or None if not found
            - str: Display name of the client
            - str: Download URL for the client
    """
    client_manager = get_client_manager(client_name)
    display_name = CLIENT_DISPLAY_NAMES.get(client_name, client_name)
    download_url = CLIENT_URLS.get(client_name, "")
    
    return client_manager, display_name, download_url


def get_active_client() -> str:
    """
    Get the active client name from the config manager
    
    Returns:
        str: Name of the active client
    """
    return config_manager.get_active_client()


def get_active_client_manager() -> Optional[BaseClientManager]:
    """
    Get the client manager for the active client
    
    Returns:
        BaseClientManager: Client manager instance for the active client, or None if not found
    """
    active_client = get_active_client()
    return get_client_manager(active_client)


def get_active_client_info() -> Tuple[Optional[BaseClientManager], str, str]:
    """
    Get the client manager and related information for the active client
    
    Returns:
        Tuple containing:
            - BaseClientManager: Client manager instance or None if not found
            - str: Display name of the client
            - str: Download URL for the client
    """
    active_client = get_active_client()
    return get_client_info(active_client)
