"""
Windsurf integration utilities for MCP
"""

import os
import json
import logging
from typing import Dict, Optional, Any
import platform

logger = logging.getLogger(__name__)

# Windsurf config paths based on platform
if platform.system() == "Darwin":  # macOS
    WINDSURF_CONFIG_PATH = os.path.expanduser("~/.codeium/windsurf/mcp_config.json")
elif platform.system() == "Windows":
    WINDSURF_CONFIG_PATH = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Codeium", "windsurf", "mcp_config.json")
else:
    # Linux
    WINDSURF_CONFIG_PATH = os.path.expanduser("~/.codeium/windsurf/mcp_config.json")

class WindsurfManager:
    """Manages Windsurf MCP server configurations"""
    
    def __init__(self, config_path: str = WINDSURF_CONFIG_PATH):
        self.config_path = config_path
        self._config = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load Windsurf configuration file"""
        if not os.path.exists(self.config_path):
            logger.warning(f"Windsurf config file not found at: {self.config_path}")
            return {"mcpServers": {}}
            
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Error parsing Windsurf config file: {self.config_path}")
            return {"mcpServers": {}}
    
    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to Windsurf config file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving Windsurf config: {str(e)}")
            return False
    
    def get_servers(self) -> Dict[str, Any]:
        """Get all MCP servers configured in Windsurf"""
        config = self._load_config()
        return config.get("mcpServers", {})
    
    def get_server(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific MCP server configuration"""
        servers = self.get_servers()
        return servers.get(server_name)
    
    def add_server(self, server_name: str, server_config: Dict[str, Any]) -> bool:
        """Add or update an MCP server in Windsurf config"""
        config = self._load_config()
        
        # Initialize mcpServers if it doesn't exist
        if "mcpServers" not in config:
            config["mcpServers"] = {}
            
        # Add or update the server
        config["mcpServers"][server_name] = server_config
        
        return self._save_config(config)
    
    def remove_server(self, server_name: str) -> bool:
        """Remove an MCP server from Windsurf config"""
        config = self._load_config()
        
        if "mcpServers" not in config or server_name not in config["mcpServers"]:
            logger.warning(f"Server not found in Windsurf config: {server_name}")
            return False
            
        # Remove the server
        del config["mcpServers"][server_name]
        
        return self._save_config(config)
        
    def is_windsurf_installed(self) -> bool:
        """Check if Windsurf is installed"""
        # Check for the presence of the Windsurf directory
        windsurf_dir = os.path.dirname(self.config_path)
        return os.path.isdir(windsurf_dir)
