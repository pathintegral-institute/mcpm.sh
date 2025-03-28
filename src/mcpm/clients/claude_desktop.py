"""
Claude Desktop integration utilities for MCP
"""

import os
import logging
import platform
from typing import Dict, Any

from mcpm.clients.base import BaseClientManager

logger = logging.getLogger(__name__)

# Claude Desktop config paths based on platform
if platform.system() == "Darwin":  # macOS
    CLAUDE_CONFIG_PATH = os.path.expanduser("~/Library/Application Support/Claude/claude_desktop_config.json")
elif platform.system() == "Windows":
    CLAUDE_CONFIG_PATH = os.path.join(os.environ.get("APPDATA", ""), "Claude", "claude_desktop_config.json")
else:
    # Linux (unsupported by Claude Desktop currently, but future-proofing)
    CLAUDE_CONFIG_PATH = os.path.expanduser("~/.config/Claude/claude_desktop_config.json")

class ClaudeDesktopManager(BaseClientManager):
    """Manages Claude Desktop MCP server configurations"""
    
    # Client information
    client_key = "claude-desktop"
    display_name = "Claude Desktop"
    download_url = "https://claude.ai/download"
    
    def __init__(self, config_path: str = CLAUDE_CONFIG_PATH):
        super().__init__(config_path)
    
    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Claude Desktop"""
        return {
            "mcpServers": {},
            "disabledServers": {}
        }
    
    # Uses base class implementation of _add_server_config
        
    # Uses base class implementation of add_server
    
    # Uses the base class implementation of _convert_to_client_format
    # which handles the core fields (command, args, env)
    
    # Uses base class implementation via from_client_format
    
    # Uses base class implementation of _convert_from_client_format
    
    def disable_server(self, server_name: str) -> bool:
        """Temporarily disable (stash) a server without removing its configuration
        
        Args:
            server_name: Name of the server to disable
            
        Returns:
            bool: Success or failure
        """
        config = self._load_config()
        
        # Check if the server exists in active servers
        if "mcpServers" not in config or server_name not in config["mcpServers"]:
            logger.warning(f"Server '{server_name}' not found in active servers")
            return False
        
        # Initialize disabledServers if it doesn't exist
        if "disabledServers" not in config:
            config["disabledServers"] = {}
        
        # Store the server config in disabled servers
        config["disabledServers"][server_name] = config["mcpServers"][server_name]
        
        # Remove from active servers
        del config["mcpServers"][server_name]
        
        return self._save_config(config)
    
    def enable_server(self, server_name: str) -> bool:
        """Re-enable (pop) a previously disabled server
        
        Args:
            server_name: Name of the server to enable
            
        Returns:
            bool: Success or failure
        """
        config = self._load_config()
        
        # Check if the server exists in disabled servers
        if "disabledServers" not in config or server_name not in config["disabledServers"]:
            logger.warning(f"Server '{server_name}' not found in disabled servers")
            return False
        
        # Initialize mcpServers if it doesn't exist
        if "mcpServers" not in config:
            config["mcpServers"] = {}
        
        # Move the server config from disabled to active
        config["mcpServers"][server_name] = config["disabledServers"][server_name]
        
        # Remove from disabled servers
        del config["disabledServers"][server_name]
        
        return self._save_config(config)
    
    def is_server_disabled(self, server_name: str) -> bool:
        """Check if a server is currently disabled (stashed)
        
        Args:
            server_name: Name of the server to check
            
        Returns:
            bool: True if server is disabled, False otherwise
        """
        config = self._load_config()
        return "disabledServers" in config and server_name in config["disabledServers"]
    
    # Uses base class implementation of remove_server
    
    # Uses base class implementation of get_server
    
    # Uses base class implementation of list_servers
