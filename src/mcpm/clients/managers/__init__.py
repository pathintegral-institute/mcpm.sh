"""
Client manager implementations for various MCP clients

This package contains specific implementations of client managers for MCP clients.
"""

from mcpm.clients.managers.claude_desktop import ClaudeDesktopManager
from mcpm.clients.managers.cursor import CursorManager
from mcpm.clients.managers.windsurf import WindsurfManager

__all__ = [
    "ClaudeDesktopManager",
    "CursorManager",
    "WindsurfManager",
]
