"""
Base client manager module that defines the interface for all client managers.
"""

import os
import json
import logging
from typing import Dict, Optional, Any, List

from mcpm.utils.server_config import ServerConfig

logger = logging.getLogger(__name__)

class BaseClientManager:
    """Base class for all client managers providing a common interface"""
    
    # Client information properties
    client_key = ""         # Client identifier (e.g., "claude-desktop")
    display_name = ""      # Human-readable name (e.g., "Claude Desktop")
    download_url = ""      # URL to download the client
    
    def __init__(self, config_path: str):
        """Initialize with a configuration path"""
        self.config_path = config_path
        self._config = None
    
    def _load_config(self) -> Dict[str, Any]:
        """Load client configuration file
        
        Returns:
            Dict containing the client configuration
        """
        if not os.path.exists(self.config_path):
            logger.warning(f"Client config file not found at: {self.config_path}")
            return self._get_empty_config()
            
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Error parsing client config file: {self.config_path}")
            
            # Backup the corrupt file
            if os.path.exists(self.config_path):
                backup_path = f"{self.config_path}.bak"
                try:
                    os.rename(self.config_path, backup_path)
                    logger.info(f"Backed up corrupt config file to: {backup_path}")
                except Exception as e:
                    logger.error(f"Failed to backup corrupt file: {str(e)}")
            
            # Return empty config
            return self._get_empty_config()
    
    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to client config file
        
        Args:
            config: Configuration to save
            
        Returns:
            bool: Success or failure
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving client config: {str(e)}")
            return False
    
    def _get_empty_config(self) -> Dict[str, Any]:
        """Get an empty config structure for this client
        
        Returns:
            Dict containing empty configuration structure
        """
        # To be overridden by subclasses
        return {"mcpServers": {}}
    
    def get_servers(self) -> Dict[str, Any]:
        """Get all MCP servers configured for this client
        
        Returns:
            Dict of server configurations by name
        """
        # To be overridden by subclasses
        config = self._load_config()
        return config.get("mcpServers", {})
    
    def get_server(self, server_name: str) -> Optional[ServerConfig]:
        """Get a server configuration
        
        Args:
            server_name: Name of the server
            
        Returns:
            ServerConfig object if found, None otherwise
        """
        servers = self.get_servers()
        
        # Check if the server exists
        if server_name not in servers:
            logger.debug(f"Server {server_name} not found in {self.display_name} config")
            return None
            
        # Get the server config and convert to ServerConfig
        client_config = servers[server_name]
        return self._convert_from_client_format(server_name, client_config)
    
    def _add_server_config(self, server_name: str, server_config: Dict[str, Any]) -> bool:
        """Add or update an MCP server in client config using raw config dictionary
        
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
            server_config: StandardServer configuration object
            
        Returns:
            bool: Success or failure
        """
        # Default implementation - can be overridden by subclasses
        return self._add_server_config(server_config.name, self._convert_to_client_format(server_config))
    
    def _convert_to_client_format(self, server_config: ServerConfig) -> Dict[str, Any]:
        """Convert ServerConfig to client-specific format with common core fields
        
        This base implementation provides the common core fields (command, args, env)
        that are used by all client managers. Subclasses can override this method
        if they need to add additional client-specific fields.
        
        Args:
            server_config: ServerConfig object
            
        Returns:
            Dict containing client-specific configuration with core fields
        """
        # Base result containing only essential execution information
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
    def from_client_format(cls, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert client format to ServerConfig
        
        This is a helper method used by subclasses to convert from client-specific format to ServerConfig.
        
        Args:
            server_name: Name of the server
            client_config: Client-specific configuration
            
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
            
        return ServerConfig.from_dict(server_data)
    
    def _convert_from_client_format(self, server_name: str, client_config: Any) -> ServerConfig:
        """Convert client-specific format to ServerConfig
        
        This default implementation handles the case where client_config might be a ServerConfig already
        or needs to be converted using from_client_format.
        
        Args:
            server_name: Name of the server
            client_config: Client-specific configuration or ServerConfig object
            
        Returns:
            ServerConfig object
        """
        # If client_config is already a ServerConfig object, just return it
        if isinstance(client_config, ServerConfig):
            # Ensure the name is set correctly
            if client_config.name != server_name:
                client_config.name = server_name
            return client_config
        
        # Otherwise, convert from dict format
        return self.from_client_format(server_name, client_config)
        
    def list_servers(self) -> List[str]:
        """List all MCP servers in client config
        
        Returns:
            List of server names
        """
        config = self._load_config()
        
        # Check if mcpServers exists
        if "mcpServers" not in config:
            return []
            
        return list(config["mcpServers"].keys())
    
    def get_server_configs(self) -> List[ServerConfig]:
        """Get all MCP servers as ServerConfig objects
        
        Returns:
            List of ServerConfig objects
        """
        servers = self.get_servers()
        return [
            self._convert_from_client_format(name, config) 
            for name, config in servers.items()
        ]
    
    def get_server_config(self, server_name: str) -> Optional[ServerConfig]:
        """Get a specific MCP server as a ServerConfig object
        
        Args:
            server_name: Name of the server
            
        Returns:
            ServerConfig or None if not found
        """
        server = self.get_server(server_name)
        if server:
            return self._convert_from_client_format(server_name, server)
        return None
    
    def remove_server(self, server_name: str) -> bool:
        """Remove an MCP server from client config
        
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
            logger.warning(f"Server {server_name} not found in {self.display_name} config")
            return False
            
        # Remove the server
        del config["mcpServers"][server_name]
        
        return self._save_config(config)
    
    def get_client_info(self) -> Dict[str, str]:
        """Get information about this client
        
        Returns:
            Dict: Information about the client including display name, download URL, and config path
        """
        return {
            "name": self.display_name,
            "download_url": self.download_url,
            "config_file": self.config_path
        }
    
    def is_client_installed(self) -> bool:
        """Check if this client is installed
        
        Returns:
            bool: True if client is installed, False otherwise
        """
        # Default implementation checks if the config directory exists
        # Can be overridden by subclasses
        return os.path.isdir(os.path.dirname(self.config_path))
        
    def disable_server(self, server_name: str) -> bool:
        """Temporarily disable (stash) a server without removing its configuration
        
        Args:
            server_name: Name of the server to disable
            
        Returns:
            bool: Success or failure
        """
        # To be implemented by subclasses
        raise NotImplementedError("Subclasses must implement disable_server")
    
    def enable_server(self, server_name: str) -> bool:
        """Re-enable (pop) a previously disabled server
        
        Args:
            server_name: Name of the server to enable
            
        Returns:
            bool: Success or failure
        """
        # To be implemented by subclasses
        raise NotImplementedError("Subclasses must implement enable_server")
    
    def is_server_disabled(self, server_name: str) -> bool:
        """Check if a server is currently disabled (stashed)
        
        Args:
            server_name: Name of the server to check
            
        Returns:
            bool: True if server is disabled, False otherwise
        """
        # To be implemented by subclasses
        raise NotImplementedError("Subclasses must implement is_server_disabled")
