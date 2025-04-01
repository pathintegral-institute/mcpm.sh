"""
MCPM Client package

Provides client-specific implementations and configuration
"""

from mcpm.clients.base import BaseClientManager
from mcpm.clients.claude_desktop import ClaudeDesktopManager
from mcpm.clients.client_config import ClientConfigManager
from mcpm.clients.cursor import CursorManager
from mcpm.clients.windsurf import WindsurfManager

__all__ = [
    "BaseClientManager",
    "ClaudeDesktopManager",
    "WindsurfManager",
    "CursorManager",
    "ClientConfigManager",
]
