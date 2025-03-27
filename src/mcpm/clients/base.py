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
    
    def get_server(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific MCP server configuration
        
        Args:
            server_name: Name of the server to retrieve
            
        Returns:
            Server configuration or None if not found
        """
        servers = self.get_servers()
        return servers.get(server_name)
    
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
        # To be implemented by subclasses
        raise NotImplementedError("Subclasses must implement _add_server_config")
        
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
        """Convert ServerConfig to client-specific format
        
        Args:
            server_config: StandardServer configuration
            
        Returns:
            Dict containing client-specific configuration
        """
        # To be implemented by subclasses
        raise NotImplementedError("Subclasses must implement _convert_to_client_format")
    
    def _convert_from_client_format(self, server_name: str, client_config: Dict[str, Any]) -> ServerConfig:
        """Convert client-specific format to ServerConfig
        
        Args:
            server_name: Name of the server
            client_config: Client-specific configuration
            
        Returns:
            ServerConfig object
        """
        # To be implemented by subclasses
        raise NotImplementedError("Subclasses must implement _convert_from_client_format")
        
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
        # To be implemented by subclasses
        raise NotImplementedError("Subclasses must implement remove_server")
    
    def is_client_installed(self) -> bool:
        """Check if this client is installed
        
        Returns:
            bool: True if client is installed, False otherwise
        """
        # Default implementation - can be overridden by subclasses
        client_dir = os.path.dirname(self.config_path)
        return os.path.isdir(client_dir)
        
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
