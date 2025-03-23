"""
Configuration utilities for MCP
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any

from mcp.utils.client_detector import detect_installed_clients, get_recommended_client

logger = logging.getLogger(__name__)

# Default configuration paths
DEFAULT_CONFIG_DIR = os.path.expanduser("~/.config/mcp")
DEFAULT_CONFIG_FILE = os.path.join(DEFAULT_CONFIG_DIR, "config.json")
DEFAULT_SERVERS_DIR = os.path.join(DEFAULT_CONFIG_DIR, "servers")

class ConfigManager:
    """Manages MCP configuration"""
    
    def __init__(self, config_path: str = DEFAULT_CONFIG_FILE):
        self.config_path = config_path
        self.config_dir = os.path.dirname(config_path)
        self.servers_dir = os.path.join(self.config_dir, "servers")
        self._config = None
        self._ensure_dirs()
        self._load_config()
    
    def _ensure_dirs(self) -> None:
        """Ensure all configuration directories exist"""
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.servers_dir, exist_ok=True)
    
    def _load_config(self) -> None:
        """Load configuration from file or create default"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self._config = json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Error parsing config file: {self.config_path}")
                self._config = self._default_config()
        else:
            self._config = self._default_config()
            self._save_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        # Detect installed clients and set a sensible default active client
        installed_clients = detect_installed_clients()
        recommended_client = get_recommended_client()
        
        return {
            "version": "0.1.0",
            "servers_dir": self.servers_dir,
            "active_client": recommended_client,
            "servers": {},
            "clients": {
                "claude-desktop": {
                    "enabled_servers": [],
                    "installed": installed_clients.get("claude-desktop", False)
                },
                "cursor": {
                    "enabled_servers": [],
                    "installed": installed_clients.get("cursor", False)
                },
                "windsurf": {
                    "enabled_servers": [],
                    "installed": installed_clients.get("windsurf", False)
                }
            }
        }
    
    def _save_config(self) -> None:
        """Save current configuration to file"""
        with open(self.config_path, 'w') as f:
            json.dump(self._config, f, indent=2)
    
    def get_config(self) -> Dict[str, Any]:
        """Get the complete configuration"""
        return self._config
    
    def get_server_info(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific server"""
        return self._config.get("servers", {}).get(server_name)
    
    def get_all_servers(self) -> Dict[str, Any]:
        """Get information about all installed servers"""
        return self._config.get("servers", {})
    
    def get_client_servers(self, client_name: str) -> List[str]:
        """Get servers enabled for a specific client"""
        return self._config.get("clients", {}).get(client_name, {}).get("enabled_servers", [])
    
    def register_server(self, server_name: str, server_info: Dict[str, Any]) -> None:
        """Register a new server"""
        self._config.setdefault("servers", {})[server_name] = server_info
        self._save_config()
    
    def unregister_server(self, server_name: str) -> None:
        """Unregister a server"""
        if server_name in self._config.get("servers", {}):
            del self._config["servers"][server_name]
            
            # Also remove from all clients
            for client in self._config.get("clients", {}).values():
                if "enabled_servers" in client and server_name in client["enabled_servers"]:
                    client["enabled_servers"].remove(server_name)
            
            self._save_config()
    
    def enable_server_for_client(self, server_name: str, client_name: str) -> bool:
        """Enable a server for a specific client"""
        if server_name not in self._config.get("servers", {}):
            logger.error(f"Server not installed: {server_name}")
            return False
        
        if client_name not in self._config.get("clients", {}):
            logger.error(f"Unknown client: {client_name}")
            return False
        
        enabled_servers = self._config["clients"][client_name].setdefault("enabled_servers", [])
        if server_name not in enabled_servers:
            enabled_servers.append(server_name)
            self._save_config()
        
        return True
    
    def disable_server_for_client(self, server_name: str, client_name: str) -> bool:
        """Disable a server for a specific client"""
        if client_name not in self._config.get("clients", {}):
            logger.error(f"Unknown client: {client_name}")
            return False
        
        enabled_servers = self._config["clients"][client_name].get("enabled_servers", [])
        if server_name in enabled_servers:
            enabled_servers.remove(server_name)
            self._save_config()
        
        return True
        
    def get_active_client(self) -> str:
        """Get the name of the currently active client"""
        return self._config.get("active_client", "claude-desktop")
    
    def set_active_client(self, client_name: str) -> bool:
        """Set the active client"""
        if client_name not in self._config.get("clients", {}):
            logger.error(f"Unknown client: {client_name}")
            return False
        
        self._config["active_client"] = client_name
        self._save_config()
        return True
    
    def get_supported_clients(self) -> List[str]:
        """Get a list of supported client names"""
        return list(self._config.get("clients", {}).keys())
