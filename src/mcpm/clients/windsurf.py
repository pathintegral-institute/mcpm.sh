"""
Windsurf integration utilities for MCP
"""

import os
import logging
from typing import Dict, Any, Optional, List, Union
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
        
        Following the official Windsurf MCP format as documented at
        https://docs.codeium.com/windsurf/mcp
        
        Args:
            server_config: ServerConfig object
            
        Returns:
            Dict containing Windsurf-specific configuration
        """
        # Include only the essential MCP execution fields that Windsurf requires
        # according to the documentation example: command, args, and env
        result = {
            "command": server_config.command,
            "args": server_config.args,
        }
        
        # Add filtered environment variables if present
        non_empty_env = server_config.get_filtered_env_vars()
        if non_empty_env:
            result["env"] = non_empty_env
            
        return result
    
    @classmethod
    def from_windsurf_format(cls, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert Windsurf format to ServerConfig
        
        Args:
            server_name: Name of the server
            client_config: Windsurf-specific configuration
            
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
        for field in ["display_name", "description", "installation"]:
            if field in client_config:
                server_data[field] = client_config[field]
                
        # For backward compatibility, if path, version, etc. are in the config
        # but not in ServerConfig anymore, store the installation info
        if "installation" not in server_data:
            install_details = []
            # Check for explicit installation fields
            if "installation_method" in client_config:
                install_details.append(client_config["installation_method"])
            if "installation_type" in client_config:
                install_details.append(client_config["installation_type"])
                
            # If no explicit installation info but has legacy fields,
            # create a generic installation value
            if not install_details and ("path" in client_config or "version" in client_config):
                server_data["installation"] = "legacy:import"
            elif install_details:
                server_data["installation"] = ":".join(install_details)
            
        return ServerConfig.from_dict(server_data)
    
    def _convert_from_client_format(self, server_name: str, client_config: Union[Dict[str, Any], ServerConfig]) -> ServerConfig:
        """Convert Windsurf format to ServerConfig
        
        Args:
            server_name: Name of the server
            client_config: Windsurf-specific configuration or ServerConfig object
            
        Returns:
            ServerConfig object
        """
        # If client_config is already a ServerConfig, just return it
        if isinstance(client_config, ServerConfig):
            # Ensure the name is set correctly
            if client_config.name != server_name:
                client_config.name = server_name
            return client_config
        # Otherwise, convert from dict format
        return self.from_windsurf_format(server_name, client_config)
    
    def remove_server(self, server_name: str) -> bool:
        """Remove an MCP server from Windsurf config
        
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
            logger.warning(f"Server {server_name} not found in Windsurf config")
            return False
            
        # Remove the server
        del config["mcpServers"][server_name]
        
        return self._save_config(config)
    
    def get_server(self, server_name: str) -> Optional[ServerConfig]:
        """Get a server configuration from Windsurf
        
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
            logger.debug(f"Server {server_name} not found in Windsurf config")
            return None
            
        # Get the server config and convert to StandardServer
        client_config = config["mcpServers"][server_name]
        return self._convert_from_client_format(server_name, client_config)
    
    def list_servers(self) -> List[str]:
        """List all MCP servers in Windsurf config
        
        Returns:
            List of server names
        """
        config = self._load_config()
        
        # Check if mcpServers exists
        if "mcpServers" not in config:
            return []
            
        return list(config["mcpServers"].keys())
