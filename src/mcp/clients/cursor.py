"""
Cursor client configuration for MCP
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional

# Cursor stores MCP configuration in:
# - Project config: .cursor/mcp.json in the project directory
# - Global config: ~/.cursor/mcp.json in the home directory

# Global config path for Cursor
HOME_DIR = os.path.expanduser("~")
CURSOR_CONFIG_PATH = os.path.join(HOME_DIR, ".cursor", "mcp.json")

logger = logging.getLogger(__name__)

# Get the project config path for Cursor
def get_project_config_path(project_dir: str) -> str:
    """
    Get the project-specific MCP configuration path for Cursor
    
    Args:
        project_dir (str): Project directory path
        
    Returns:
        str: Path to the project-specific MCP configuration file
    """
    return os.path.join(project_dir, ".cursor", "mcp.json")


class CursorManager:
    """Manages Cursor client configuration for MCP"""
    
    def __init__(self):
        self.config_path = CURSOR_CONFIG_PATH
    
    def is_cursor_installed(self) -> bool:
        """Check if Cursor is installed"""
        return os.path.isdir(os.path.dirname(self.config_path))
    
    def read_config(self) -> Optional[Dict[str, Any]]:
        """Read the Cursor MCP configuration"""
        if not os.path.exists(self.config_path):
            return None
            
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Error parsing Cursor config file: {self.config_path}")
            return None
        except Exception as e:
            logger.error(f"Error reading Cursor config file: {str(e)}")
            return None
    
    def write_config(self, config: Dict[str, Any]) -> bool:
        """Write the Cursor MCP configuration"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error writing Cursor config file: {str(e)}")
            return False
    
    def create_default_config(self) -> Dict[str, Any]:
        """Create a default Cursor MCP configuration"""
        return {
            "mcpServers": {}
        }
    
    def sync_mcp_servers(self, servers: List[Dict[str, Any]]) -> bool:
        """Sync MCP servers to Cursor configuration"""
        config = self.read_config() or self.create_default_config()
        
        # Update mcpServers section
        for server in servers:
            name = server.get("name")
            if name:
                config.setdefault("mcpServers", {})[name] = {
                    "command": server.get("command", ""),
                    "args": server.get("args", []),
                }
                
                # Add environment variables if present
                if "env" in server and server["env"]:
                    config["mcpServers"][name]["env"] = server["env"]
        
        # Write updated config
        return self.write_config(config)
        
    def get_servers(self) -> Dict[str, Any]:
        """Get MCP servers from Cursor configuration
        
        Returns:
            Dict[str, Any]: Dictionary mapping server names to their configurations
        """
        config = self.read_config()
        if not config:
            return {}
            
        return config.get("mcpServers", {})
