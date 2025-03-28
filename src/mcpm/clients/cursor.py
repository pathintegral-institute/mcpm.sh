"""
Cursor integration utilities for MCP
"""

import os
import logging
import platform
from typing import Dict, Any

from mcpm.clients.base import BaseClientManager

logger = logging.getLogger(__name__)

# Cursor config paths based on platform
if platform.system() == "Darwin":  # macOS
    CURSOR_CONFIG_PATH = os.path.expanduser("~/Library/Application Support/Cursor/User/mcp_config.json")
elif platform.system() == "Windows":
    CURSOR_CONFIG_PATH = os.path.join(os.environ.get("APPDATA", ""), "Cursor", "User", "mcp_config.json")
else:
    # Linux
    CURSOR_CONFIG_PATH = os.path.expanduser("~/.config/Cursor/User/mcp_config.json")

class CursorManager(BaseClientManager):
    """Manages Cursor MCP server configurations"""
    
    # Client information
    client_key = "cursor"
    display_name = "Cursor"
    download_url = "https://cursor.sh/download"
    
    def __init__(self, config_path: str = CURSOR_CONFIG_PATH):
        super().__init__(config_path)
    
    def _get_empty_config(self) -> Dict[str, Any]:
        """Get empty config structure for Cursor"""
        return {"mcpServers": {}}
    
    # Uses base class implementation of _add_server_config
        
    # Uses base class implementation of add_server
    
    # Uses the base class implementation of _convert_to_client_format
    # which handles the core fields (command, args, env)
    
    # Uses base class implementation via from_client_format
    
    # Uses base class implementation of _convert_from_client_format
    
    # Uses base class implementation of remove_server
    
    # Uses base class implementation of get_server
    
    # Uses base class implementation of list_servers
