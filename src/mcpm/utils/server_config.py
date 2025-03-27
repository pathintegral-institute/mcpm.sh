"""
Standard server configuration model for MCP.
Provides a consistent interface for server configurations across all clients.
"""

import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


@dataclass
class ServerConfig:
    """Standard model for MCP server configuration"""
    
    # Required fields
    name: str
    path: str 
    
    # Optional fields with defaults
    display_name: str = ""
    description: str = ""
    version: str = "1.0.0"
    status: str = "stopped"  # stopped, running
    command: str = ""
    args: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    install_date: str = field(default_factory=lambda: datetime.date.today().isoformat())
    installation_method: str = ""
    installation_type: str = ""
    package: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServerConfig':
        """Create ServerConfig from dictionary
        
        Args:
            data: Dictionary with server configuration data
            
        Returns:
            ServerConfig object
        """
        # Handle potential key differences in source data
        server_data = data.copy()
        
        # Handle environment variables from different formats
        if "env" in server_data and "env_vars" not in server_data:
            server_data["env_vars"] = server_data.pop("env")
        
        # Set name from the dictionary key if not in the data
        if "name" not in server_data and server_data.get("display_name"):
            server_data["name"] = server_data["display_name"].lower().replace(" ", "-")
            
        # Remove any keys that aren't in the dataclass to avoid unexpected keyword arguments
        valid_fields = {field.name for field in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in server_data.items() if k in valid_fields}
        
        return cls(**filtered_data)
    
    def to_windsurf_format(self) -> Dict[str, Any]:
        """Convert to Windsurf client format
        
        Following the official Windsurf MCP format as documented at
        https://docs.codeium.com/windsurf/mcp
        
        Returns:
            Dictionary in Windsurf format with only essential fields
        """
        # Include only the essential MCP execution fields that Windsurf requires
        # according to the documentation example: command, args, and env
        result = {
            "command": self.command,
            "args": self.args,
        }
        
        # Add environment variables if present
        if self.env_vars:
            result["env"] = self.env_vars
            
        return result
    
    def to_claude_desktop_format(self) -> Dict[str, Any]:
        """Convert to Claude Desktop client format
        
        Returns:
            Dictionary in Claude Desktop format
        """
        return {
            "name": self.name,
            "display_name": self.display_name or f"{self.name.title()} MCP Server",
            "version": self.version,
            "description": self.description,
            "status": self.status,
            "install_date": self.install_date,
            "path": self.path,
            "command": self.command,
            "args": self.args,
            "env": self.env_vars
        }
    
    def to_cursor_format(self) -> Dict[str, Any]:
        """Convert to Cursor client format
        
        Returns:
            Dictionary in Cursor format
        """
        return {
            "name": self.name,
            "display_name": self.display_name or f"{self.name.title()} MCP Server",
            "version": self.version,
            "description": self.description,
            "status": self.status,
            "path": self.path,
            "command": self.command,
            "args": self.args,
            "env": self.env_vars
        }
    
    @classmethod
    def from_windsurf_format(cls, name: str, data: Dict[str, Any]) -> 'ServerConfig':
        """Create ServerConfig from Windsurf format
        
        Args:
            name: Server name
            data: Windsurf format server data
            
        Returns:
            ServerConfig object
        """
        server_data = data.copy()
        server_data["name"] = name
        
        # Handle required fields that might be missing in the Windsurf format
        # Path is required by ServerConfig but not part of the Windsurf MCP format
        if "path" not in server_data:
            server_data["path"] = f"/path/to/{name}"
            
        # Convert environment variables if present
        if "env" in server_data and "env_vars" not in server_data:
            server_data["env_vars"] = server_data.pop("env")
        
        return cls.from_dict(server_data)
    
    @classmethod
    def from_claude_desktop_format(cls, name: str, data: Dict[str, Any]) -> 'ServerConfig':
        """Create ServerConfig from Claude Desktop format
        
        Args:
            name: Server name
            data: Claude Desktop format server data
            
        Returns:
            ServerConfig object
        """
        server_data = data.copy()
        server_data["name"] = name
        return cls.from_dict(server_data)
    
    @classmethod
    def from_cursor_format(cls, name: str, data: Dict[str, Any]) -> 'ServerConfig':
        """Create ServerConfig from Cursor format
        
        Args:
            name: Server name
            data: Cursor format server data
            
        Returns:
            ServerConfig object
        """
        server_data = data.copy()
        server_data["name"] = name
        return cls.from_dict(server_data)
