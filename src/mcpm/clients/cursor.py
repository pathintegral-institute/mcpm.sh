"""
Cursor client configuration for MCP
"""

import os
import logging
from typing import Dict, Any

from mcpm.clients.base import BaseClientManager
from mcpm.utils.server_config import ServerConfig

# Cursor stores MCP configuration in:
# - Project config: .cursor/mcp.json in the project directory
# - Global config: ~/.cursor/mcp.json in the home directory

# Global config path for Cursor
HOME_DIR = os.path.expanduser("~")
CURSOR_CONFIG_PATH = os.path.join(HOME_DIR, ".cursor", "mcp.json")

logger = logging.getLogger(__name__)

# Get the project config path for Cursor
def get_project_config_path(project_dir: str) -> str:
    """
    Get the project-specific MCP configuration path for Cursor
    
    Args:
        project_dir (str): Project directory path
        
    Returns:
        str: Path to the project-specific MCP configuration file
    """
    return os.path.join(project_dir, ".cursor", "mcp.json")


class CursorManager(BaseClientManager):
    """Manages Cursor client configuration for MCP"""
    
    def __init__(self, config_path: str = CURSOR_CONFIG_PATH):
        super().__init__(config_path)
    
    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Cursor"""
        return {"mcpServers": {}}
    
    def _add_server_config(self, server_name: str, server_config: Dict[str, Any]) -> bool:
        """Add or update an MCP server in Cursor config using raw config dictionary
        
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
        """Convert ServerConfig to Cursor format
        
        Args:
            server_config: StandardServer configuration
            
        Returns:
            Dict containing Cursor-specific configuration
        """
        return server_config.to_cursor_format()
    
    def _convert_from_client_format(self, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert Cursor format to ServerConfig
        
        Args:
            server_name: Name of the server
            client_config: Cursor-specific configuration
            
        Returns:
            ServerConfig object
        """
        return ServerConfig.from_cursor_format(server_name, client_config)
    
    def remove_server(self, server_name: str) -> bool:
        """Remove an MCP server from Cursor config
        
        Args:
            server_name: Name of the server to remove
            
        Returns:
            bool: Success or failure
        """
        config = self._load_config()
        
        if "mcpServers" not in config or server_name not in config["mcpServers"]:
            logger.warning(f"Server not found in Cursor config: {server_name}")
            return False
            
        # Remove the server
        del config["mcpServers"][server_name]
        
        return self._save_config(config)
    
    def is_cursor_installed(self) -> bool:
        """Check if Cursor is installed"""
        return self.is_client_installed()
