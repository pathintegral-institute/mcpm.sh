"""
Claude Desktop integration utilities for MCP
"""

import os
import logging
import platform
from typing import Dict, Any

from mcpm.clients.base import BaseClientManager
from mcpm.utils.server_config import ServerConfig

logger = logging.getLogger(__name__)

# Claude Desktop config paths based on platform
if platform.system() == "Darwin":  # macOS
    CLAUDE_CONFIG_PATH = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
elif platform.system() == "Windows":
    CLAUDE_CONFIG_PATH = os.path.join(os.environ.get("APPDATA", ""), "Claude", "claude_desktop_config.json")
else:
    # Linux (unsupported by Claude Desktop currently, but future-proofing)
    CLAUDE_CONFIG_PATH = os.path.expanduser("~/.config/Claude/claude_desktop_config.json")

class ClaudeDesktopManager(BaseClientManager):
    """Manages Claude Desktop MCP server configurations"""
    
    def __init__(self, config_path: str = CLAUDE_CONFIG_PATH):
        super().__init__(config_path)
    
    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Claude Desktop"""
        return {"mcpServers": {}}
    
    def _add_server_config(self, server_name: str, server_config: Dict[str, Any]) -> bool:
        """Add or update an MCP server in Claude Desktop config using raw config dictionary
        
        Note: This is an internal method that should generally not be called directly.
        Use add_server with a ServerConfig object instead for better type safety and validation.
        
        Args:
            server_name: Name of the server
            server_config: Server configuration dictionary
            
        Returns:
            bool: Success or failure
        """
        config = self._load_config()
        
        # Initialize mcpServers if it doesn't exist
        if "mcpServers" not in config:
            config["mcpServers"] = {}
            
        # Add or update the server
        config["mcpServers"][server_name] = server_config
        
        return self._save_config(config)
        
    def add_server(self, server_config: ServerConfig) -> bool:
        """Add or update a server using a ServerConfig object
        
        This is the preferred method for adding servers as it ensures proper type safety
        and validation through the ServerConfig object.
        
        Args:
            server_config: ServerConfig object
            
        Returns:
            bool: Success or failure
        """
        client_config = self._convert_to_client_format(server_config)
        return self._add_server_config(server_config.name, client_config)
    
    def _convert_to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert ServerConfig to Claude Desktop format
        
        Args:
            server_config: StandardServer configuration
            
        Returns:
            Dict containing Claude Desktop-specific configuration
        """
        return server_config.to_claude_desktop_format()
    
    def _convert_from_client_format(self, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert Claude Desktop format to ServerConfig
        
        Args:
            server_name: Name of the server
            client_config: Claude Desktop-specific configuration
            
        Returns:
            ServerConfig object
        """
        return ServerConfig.from_claude_desktop_format(server_name, client_config)
    
    def remove_server(self, server_name: str) -> bool:
        """Remove an MCP server from Claude Desktop config"""
        config = self._load_config()
        
        if "mcpServers" not in config or server_name not in config["mcpServers"]:
            logger.warning(f"Server not found in Claude Desktop config: {server_name}")
            return False
            
        # Remove the server
        del config["mcpServers"][server_name]
        
        return self._save_config(config)
    
    def is_claude_desktop_installed(self) -> bool:
        """Check if Claude Desktop is installed"""
        return self.is_client_installed()
