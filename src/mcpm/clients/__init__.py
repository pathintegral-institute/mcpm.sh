"""
Client integrations for MCPM - manages client-specific configurations
"""

from mcpm.clients.claude_desktop import ClaudeDesktopManager
from mcpm.clients.windsurf import WindsurfManager

__all__ = ['ClaudeDesktopManager', 'WindsurfManager']
