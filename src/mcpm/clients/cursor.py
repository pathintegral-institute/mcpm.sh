"""
Cursor integration utilities for MCP
"""

import os
import logging
import platform
from typing import Dict, Any, Optional, List

from mcpm.clients.base import BaseClientManager
from mcpm.utils.server_config import ServerConfig

logger = logging.getLogger(__name__)

# Cursor config paths based on platform
if platform.system() == "Darwin":  # macOS
    CURSOR_CONFIG_PATH = os.path.expanduser("~/Library/Application Support/Cursor/User/mcp_config.json")
elif platform.system() == "Windows":
    CURSOR_CONFIG_PATH = os.path.join(os.environ.get("APPDATA", ""), "Cursor", "User", "mcp_config.json")
else:
    # Linux
    CURSOR_CONFIG_PATH = os.path.expanduser("~/.config/Cursor/User/mcp_config.json")

class CursorManager(BaseClientManager):
    """Manages Cursor MCP server configurations"""
    
    # Client information
    client_key = "cursor"
    display_name = "Cursor"
    download_url = "https://cursor.sh/download"
    
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
            server_config: ServerConfig object
            
        Returns:
            Dict containing Cursor-specific configuration
        """
        # Base result containing essential execution information
        result = {
            "command": server_config.command,
            "args": server_config.args,
        }
        
        # Add filtered environment variables if present
        non_empty_env = server_config.get_filtered_env_vars()
        if non_empty_env:
            result["env"] = non_empty_env
            
        # Add additional metadata fields for display in Cursor
        # Fields that are None will be automatically excluded by JSON serialization
        for field in ["name", "display_name", "description", "version", "status", "path", "install_date"]:
            value = getattr(server_config, field, None)
            if value is not None:
                result[field] = value
                
        return result
    
    @classmethod
    def from_cursor_format(cls, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert Cursor format to ServerConfig
        
        Args:
            server_name: Name of the server
            client_config: Cursor-specific configuration
            
        Returns:
            ServerConfig object
        """
        # Create a dictionary that ServerConfig.from_dict can work with
        server_data = {
            "name": server_name,
            "command": client_config.get("command", ""),
            "args": client_config.get("args", []),
        }
        
        # Add environment variables if present
        if "env" in client_config:
            server_data["env_vars"] = client_config["env"]
            
        # Add additional metadata fields if present
        for field in ["display_name", "description", "version", "status", "path", "install_date", 
                     "package", "installation_method", "installation_type"]:
            if field in client_config:
                server_data[field] = client_config[field]
                
        return ServerConfig.from_dict(server_data)
    
    def _convert_from_client_format(self, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert Cursor format to ServerConfig
        
        Args:
            server_name: Name of the server
            client_config: Cursor-specific configuration
            
        Returns:
            ServerConfig object
        """
        return self.from_cursor_format(server_name, client_config)
    
    def remove_server(self, server_name: str) -> bool:
        """Remove an MCP server from Cursor config
        
        Args:
            server_name: Name of the server to remove
            
        Returns:
            bool: Success or failure
        """
        config = self._load_config()
        
        # Check if mcpServers exists
        if "mcpServers" not in config:
            logger.warning(f"Cannot remove server {server_name}: mcpServers section doesn't exist")
            return False
            
        # Check if the server exists
        if server_name not in config["mcpServers"]:
            logger.warning(f"Server {server_name} not found in Cursor config")
            return False
            
        # Remove the server
        del config["mcpServers"][server_name]
        
        return self._save_config(config)
    
    def get_server(self, server_name: str) -> Optional[ServerConfig]:
        """Get a server configuration from Cursor
        
        Args:
            server_name: Name of the server
            
        Returns:
            ServerConfig object if found, None otherwise
        """
        config = self._load_config()
        
        # Check if mcpServers exists
        if "mcpServers" not in config:
            logger.warning(f"Cannot get server {server_name}: mcpServers section doesn't exist")
            return None
            
        # Check if the server exists
        if server_name not in config["mcpServers"]:
            logger.debug(f"Server {server_name} not found in Cursor config")
            return None
            
        # Get the server config and convert to StandardServer
        client_config = config["mcpServers"][server_name]
        return self._convert_from_client_format(server_name, client_config)
    
    def list_servers(self) -> List[str]:
        """List all MCP servers in Cursor config
        
        Returns:
            List of server names
        """
        config = self._load_config()
        
        # Check if mcpServers exists
        if "mcpServers" not in config:
            return []
            
        return list(config["mcpServers"].keys())
