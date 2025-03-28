"""
Windsurf integration utilities for MCP
"""

import os
import logging
import platform
from typing import Dict, Any

from mcpm.clients.base import BaseClientManager

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
    
    # Client information
    client_key = "windsurf"
    display_name = "Windsurf"
    download_url = "https://codeium.com/windsurf/download"
    
    def __init__(self, config_path: str = WINDSURF_CONFIG_PATH):
        super().__init__(config_path)
        
    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Windsurf"""
        return {"mcpServers": {}}
    
    def _add_server_config(self, server_name: str, server_config: Dict[str, Any]) -> bool:
        """Add or update an MCP server in Windsurf config with additional validation
        
        Extends the base implementation with Windsurf-specific validation.
        
        Args:
            server_name: Name of the server
            server_config: Server configuration dictionary
            
        Returns:
            bool: Success or failure
        """
        # Validate required fields - just log a warning but don't block
        if "command" not in server_config:
            logger.warning(f"Server config for {server_name} is missing 'command' field")
        
        # Use the base class implementation for the actual update
        return super()._add_server_config(server_name, server_config)
        
    # Uses base class implementation of add_server
        
    # Uses the base class implementation of _convert_to_client_format
    # which handles the core fields (command, args, env) as documented at
    # https://docs.codeium.com/windsurf/mcp
    
    # Uses base class implementation via from_client_format
    
    # Uses base class implementation of _convert_from_client_format
    
    # Uses base class implementation of remove_server
    
    # Uses base class implementation of get_server
    
    # Uses base class implementation of list_servers
