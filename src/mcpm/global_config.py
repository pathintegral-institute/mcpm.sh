"""
Global server configuration management for MCPM v2.0

This module manages the global server registry where all servers are stored centrally.
Profiles tag servers but don't own them - servers exist globally.
"""

import json
import logging
import os
from typing import Dict, List, Optional

from pydantic import TypeAdapter

from mcpm.core.schema import ServerConfig

DEFAULT_GLOBAL_CONFIG_PATH = os.path.expanduser("~/.config/mcpm/servers.json")

logger = logging.getLogger(__name__)


class GlobalConfigManager:
    """Manages the global MCPM server configuration.
    
    In v2.0, all servers are stored in a single global configuration file.
    Profiles organize servers via tagging, but servers exist independently.
    """

    def __init__(self, config_path: str = DEFAULT_GLOBAL_CONFIG_PATH):
        self.config_path = os.path.expanduser(config_path)
        self.config_dir = os.path.dirname(self.config_path)
        self._servers: Dict[str, ServerConfig] = self._load_servers()
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Ensure all configuration directories exist"""
        os.makedirs(self.config_dir, exist_ok=True)

    def _load_servers(self) -> Dict[str, ServerConfig]:
        """Load servers from the global configuration file."""
        if not os.path.exists(self.config_path):
            return {}
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                servers_data = json.load(f) or {}
        except json.JSONDecodeError as e:
            logger.error(f"Error loading global servers from {self.config_path}: {e}")
            return {}
        
        servers = {}
        for name, config_data in servers_data.items():
            try:
                servers[name] = TypeAdapter(ServerConfig).validate_python(config_data)
            except Exception as e:
                logger.error(f"Error loading server {name}: {e}")
                continue
                
        return servers

    def _save_servers(self) -> None:
        """Save servers to the global configuration file."""
        self._ensure_dirs()
        servers_data = {name: config.model_dump() for name, config in self._servers.items()}
        
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(servers_data, f, indent=2)

    def add_server(self, server_config: ServerConfig, force: bool = False) -> bool:
        """Add a server to the global configuration.
        
        Args:
            server_config: The server configuration to add
            force: Whether to overwrite existing server
            
        Returns:
            bool: Success or failure
        """
        if server_config.name in self._servers and not force:
            logger.warning(f"Server '{server_config.name}' already exists")
            return False
            
        self._servers[server_config.name] = server_config
        self._save_servers()
        return True

    def remove_server(self, server_name: str) -> bool:
        """Remove a server from the global configuration.
        
        Args:
            server_name: Name of the server to remove
            
        Returns:
            bool: Success or failure
        """
        if server_name not in self._servers:
            logger.warning(f"Server '{server_name}' not found")
            return False
            
        del self._servers[server_name]
        self._save_servers()
        return True

    def get_server(self, server_name: str) -> Optional[ServerConfig]:
        """Get a server configuration by name.
        
        Args:
            server_name: Name of the server
            
        Returns:
            ServerConfig or None if not found
        """
        return self._servers.get(server_name)

    def list_servers(self) -> Dict[str, ServerConfig]:
        """Get all servers in the global configuration.
        
        Returns:
            Dict mapping server names to configurations
        """
        return self._servers.copy()

    def server_exists(self, server_name: str) -> bool:
        """Check if a server exists in the global configuration.
        
        Args:
            server_name: Name of the server
            
        Returns:
            bool: True if server exists
        """
        return server_name in self._servers

    def update_server(self, server_config: ServerConfig) -> bool:
        """Update an existing server configuration.
        
        Args:
            server_config: Updated server configuration
            
        Returns:
            bool: Success or failure
        """
        if server_config.name not in self._servers:
            logger.warning(f"Server '{server_config.name}' not found for update")
            return False
            
        self._servers[server_config.name] = server_config
        self._save_servers()
        return True