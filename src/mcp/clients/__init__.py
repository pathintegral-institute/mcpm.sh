"""
Client integrations for MCP - manages client-specific configurations
"""

from mcp.clients.claude_desktop import ClaudeDesktopManager
from mcp.clients.windsurf import WindsurfManager

__all__ = ['ClaudeDesktopManager', 'WindsurfManager']
