"""
Client detector utility for MCP
"""

import os
from typing import Dict

from mcp.clients.claude_desktop import CLAUDE_CONFIG_PATH
from mcp.clients.windsurf import WINDSURF_CONFIG_PATH

def detect_installed_clients() -> Dict[str, bool]:
    """
    Detect which MCP-compatible clients are installed on the system
    
    Returns:
        Dict[str, bool]: Dictionary mapping client names to installed status
    """
    claude_installed = os.path.isdir(os.path.dirname(CLAUDE_CONFIG_PATH))
    windsurf_installed = os.path.isdir(os.path.dirname(WINDSURF_CONFIG_PATH))
    
    return {
        "claude-desktop": claude_installed,
        "windsurf": windsurf_installed,
        "cursor": False  # Not implemented yet
    }

def get_client_config_paths() -> Dict[str, str]:
    """
    Get the configuration file paths for all supported clients
    
    Returns:
        Dict[str, str]: Dictionary mapping client names to config file paths
    """
    return {
        "claude-desktop": CLAUDE_CONFIG_PATH,
        "windsurf": WINDSURF_CONFIG_PATH
    }

def get_client_display_info() -> Dict[str, Dict[str, str]]:
    """
    Get display information for supported clients
    
    Returns:
        Dict[str, Dict[str, str]]: Dictionary mapping client names to display information
    """
    return {
        "claude-desktop": {
            "name": "Claude Desktop",
            "download_url": "https://claude.ai/download",
            "config_file": CLAUDE_CONFIG_PATH
        },
        "windsurf": {
            "name": "Windsurf",
            "download_url": "https://codeium.com/windsurf/download",
            "config_file": WINDSURF_CONFIG_PATH
        },
        "cursor": {
            "name": "Cursor",
            "download_url": "https://cursor.sh/download",
            "config_file": "" # Not implemented yet
        }
    }

def get_recommended_client() -> str:
    """
    Get the recommended client based on installation status
    
    Returns:
        str: Name of the recommended client
    """
    clients = detect_installed_clients()
    
    # Prioritize clients that are actually installed
    for client, installed in clients.items():
        if installed:
            return client
    
    # Default to claude-desktop if nothing is installed
    return "claude-desktop"
