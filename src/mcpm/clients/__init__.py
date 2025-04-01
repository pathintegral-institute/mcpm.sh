"""
MCPM Client package

Provides client-specific implementations and configuration
"""

from mcpm.clients.base import BaseClientManager
from mcpm.clients.client_config import ClientConfigManager
from mcpm.clients.client_registry import ClientRegistry
from mcpm.clients.managers.claude_desktop import ClaudeDesktopManager
from mcpm.clients.managers.cursor import CursorManager
from mcpm.clients.managers.windsurf import WindsurfManager

__all__ = [
    "BaseClientManager",
    "ClaudeDesktopManager",
    "WindsurfManager",
    "CursorManager",
    "ClientConfigManager",
    "ClientRegistry",
]
