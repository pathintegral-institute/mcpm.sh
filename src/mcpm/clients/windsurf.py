"""
Windsurf integration utilities for MCP
"""

import os
import logging
from typing import Dict, Any, Optional, List
import platform

from mcpm.clients.base import BaseClientManager
from mcpm.utils.server_config import ServerConfig

logger = logging.getLogger(__name__)

# Windsurf config paths based on platform
if platform.system() == "Darwin":  # macOS
    WINDSURF_CONFIG_PATH = os.path.expanduser("~/.codeium/windsurf/mcp_config.json")
elif platform.system() == "Windows":
    WINDSURF_CONFIG_PATH = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Codeium", "windsurf", "mcp_config.json")
else:
    # Linux
    WINDSURF_CONFIG_PATH = os.path.expanduser("~/.codeium/windsurf/mcp_config.json")

class WindsurfManager(BaseClientManager):
    """Manages Windsurf MCP server configurations"""
    
    def __init__(self, config_path: str = WINDSURF_CONFIG_PATH):
        super().__init__(config_path)
        
    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Windsurf"""
        return {"mcpServers": {}}
    
    def _add_server_config(self, server_name: str, server_config: Dict[str, Any]) -> bool:
        """Add or update an MCP server in Windsurf config using raw config dictionary
        
        Note: This is an internal method that should generally not be called directly.
        Use add_server with a ServerConfig object instead for better type safety and validation.
        
        Args:
            server_name: Name of the server
            server_config: Server configuration dictionary
            
        Returns:
            bool: Success or failure
        """
        # Validate required fields - just log a warning but don't block
        if "command" not in server_config:
            logger.warning(f"Server config for {server_name} is missing 'command' field")
        
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
        """Convert ServerConfig to Windsurf format
        
        Args:
            server_config: StandardServer configuration
            
        Returns:
            Dict containing Windsurf-specific configuration
        """
        # Use the to_windsurf_format method which now handles all required fields
        # This includes command, args, env, path and other metadata fields
        return server_config.to_windsurf_format()
    
    def _convert_from_client_format(self, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert Windsurf format to ServerConfig
        
        Args:
            server_name: Name of the server
            client_config: Windsurf-specific configuration
            
        Returns:
            ServerConfig object
        """
        # Simply use the ServerConfig.from_windsurf_format method
        # This internally calls from_dict which handles conversion of env to env_vars
        return ServerConfig.from_windsurf_format(server_name, client_config)
    
    def remove_server(self, server_name: str) -> bool:
        """Remove an MCP server from Windsurf config
        
        Args:
            server_name: Name of the server to remove
            
        Returns:
            bool: Success or failure
        """
        config = self._load_config()
        
        if "mcpServers" not in config or server_name not in config["mcpServers"]:
            logger.warning(f"Server not found in Windsurf config: {server_name}")
            return False
            
        # Remove the server
        del config["mcpServers"][server_name]
        
        return self._save_config(config)
    
    def is_windsurf_installed(self) -> bool:
        """Check if Windsurf is installed
        
        Returns:
            bool: True if Windsurf is installed, False otherwise
        """
        return self.is_client_installed()
    
    def get_servers(self) -> Dict[str, Any]:
        """Get all MCP servers from the Windsurf config
        
        Returns:
            Dict of server configurations by name
        """
        config = self._load_config()
        return config.get("mcpServers", {})
    
    def get_server(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific MCP server from the Windsurf config
        
        Args:
            server_name: Name of the server to retrieve
            
        Returns:
            Server configuration dictionary or None if not found
        """
        servers = self.get_servers()
        return servers.get(server_name)
    
    def get_server_config(self, server_name: str) -> Optional[ServerConfig]:
        """Get a specific MCP server config as a ServerConfig object
        
        Args:
            server_name: Name of the server to retrieve
            
        Returns:
            ServerConfig object or None if server not found
        """
        client_config = self.get_server(server_name)
        if client_config is None:
            return None
        return self._convert_from_client_format(server_name, client_config)
    
    def get_server_configs(self) -> List[ServerConfig]:
        """Get all MCP server configs as ServerConfig objects
        
        Returns:
            List of ServerConfig objects
        """
        servers = self.get_servers()
        return [self._convert_from_client_format(name, config) 
                for name, config in servers.items()]
