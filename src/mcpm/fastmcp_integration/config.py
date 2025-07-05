"""
Pydantic models for FastMCP configuration to ensure correct format.
"""

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class StdioMCPServer(BaseModel):
    """Configuration for stdio-based MCP server in FastMCP format."""

    command: str = Field(..., description="Command to run the server (as string, not list)")
    args: Optional[List[str]] = Field(default=None, description="Arguments for the command")
    env: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")


class RemoteMCPServer(BaseModel):
    """Configuration for remote MCP server (HTTP/SSE) in FastMCP format."""

    url: str = Field(..., description="URL of the remote MCP server")
    headers: Optional[Dict[str, str]] = Field(default=None, description="HTTP headers to send")


# Use Union type for server configurations
MCPServerConfig = Union[StdioMCPServer, RemoteMCPServer]


class MCPConfig(BaseModel):
    """FastMCP configuration format for proxy servers."""

    model_config = ConfigDict(extra="allow")  # Allow additional fields for extensibility

    mcpServers: Dict[str, MCPServerConfig] = Field(..., description="Map of server name to server config")


def create_stdio_server_config(
    command: str, args: Optional[List[str]] = None, env: Optional[Dict[str, str]] = None
) -> StdioMCPServer:
    """Create a stdio server configuration for FastMCP."""
    return StdioMCPServer(command=command, args=args, env=env)


def create_remote_server_config(url: str, headers: Optional[Dict[str, str]] = None) -> RemoteMCPServer:
    """Create a remote server configuration for FastMCP."""
    return RemoteMCPServer(url=url, headers=headers)


def create_mcp_config(servers: Dict[str, MCPServerConfig]) -> MCPConfig:
    """Create a complete MCP configuration for FastMCP."""
    return MCPConfig(mcpServers=servers)
