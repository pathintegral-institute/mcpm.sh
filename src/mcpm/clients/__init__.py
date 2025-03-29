"""
Client integrations for MCPM - manages client-specific configurations
"""

from mcpm.clients.base import BaseClientManager
from mcpm.clients.claude_desktop import ClaudeDesktopManager
from mcpm.clients.windsurf import WindsurfManager
from mcpm.clients.cursor import CursorManager

__all__ = ["BaseClientManager", "ClaudeDesktopManager", "WindsurfManager", "CursorManager"]
