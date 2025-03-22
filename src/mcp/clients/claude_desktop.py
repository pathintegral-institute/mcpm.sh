"""
Claude Desktop integration utilities for MCP
"""

import os
import json
import logging
from typing import Dict, Optional, Any
import platform

logger = logging.getLogger(__name__)

# Claude Desktop config paths based on platform
if platform.system() == "Darwin":  # macOS
    CLAUDE_CONFIG_PATH = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
elif platform.system() == "Windows":
    CLAUDE_CONFIG_PATH = os.path.join(os.environ.get("APPDATA", ""), "Claude", "claude_desktop_config.json")
else:
    # Linux (unsupported by Claude Desktop currently, but future-proofing)
    CLAUDE_CONFIG_PATH = os.path.expanduser("~/.config/Claude/claude_desktop_config.json")

class ClaudeDesktopManager:
    """Manages Claude Desktop MCP server configurations"""
    
    def __init__(self, config_path: str = CLAUDE_CONFIG_PATH):
        self.config_path = config_path
        self._config = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load Claude Desktop configuration file"""
        if not os.path.exists(self.config_path):
            logger.warning(f"Claude Desktop config file not found at: {self.config_path}")
            return {"mcpServers": {}}
            
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Error parsing Claude Desktop config file: {self.config_path}")
            return {"mcpServers": {}}
    
    def _save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to Claude Desktop config file"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving Claude Desktop config: {str(e)}")
            return False
    
    def get_servers(self) -> Dict[str, Any]:
        """Get all MCP servers configured in Claude Desktop"""
        config = self._load_config()
        return config.get("mcpServers", {})
    
    def get_server(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific MCP server configuration"""
        servers = self.get_servers()
        return servers.get(server_name)
    
    def add_server(self, server_name: str, server_config: Dict[str, Any]) -> bool:
        """Add or update an MCP server in Claude Desktop config"""
        config = self._load_config()
        
        # Initialize mcpServers if it doesn't exist
        if "mcpServers" not in config:
            config["mcpServers"] = {}
            
        # Add or update the server
        config["mcpServers"][server_name] = server_config
        
        return self._save_config(config)
    
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
        # Check for the presence of the Claude Desktop directory
        claude_dir = os.path.dirname(self.config_path)
        return os.path.isdir(claude_dir)
