"""
FastMCP proxy factory for MCPM server aggregation.
"""

import logging
from typing import Dict, List, Optional

from fastmcp import FastMCP
from fastmcp.utilities.mcp_config import (
    MCPConfig,
    RemoteMCPServer,
    StdioMCPServer,
)

from mcpm.core.schema import CustomServerConfig, RemoteServerConfig, ServerConfig, STDIOServerConfig
from mcpm.monitor.base import AccessMonitor, SessionTransport
from mcpm.monitor.sqlite import SQLiteAccessMonitor

# FastMCP config models are available if needed in the future
# from .config import create_mcp_config, create_stdio_server_config, create_remote_server_config
from .middleware import MCPMAuthMiddleware, MCPMUnifiedTrackingMiddleware

logger = logging.getLogger(__name__)


class MCPMProxyFactory:
    """Factory for creating FastMCP proxies with MCPM integration."""

    def __init__(
        self,
        auth_enabled: bool = False,
        api_key: Optional[str] = None,
        access_monitor: Optional[AccessMonitor] = None,
    ):
        """
        Initialize the proxy factory.

        Args:
            auth_enabled: Whether authentication is enabled.
            api_key: The API key to use for authentication.
            access_monitor: Access monitor for tracking. If None, creates DuckDBMonitor.
        """
        self.auth_enabled = auth_enabled
        self.api_key = api_key

        if access_monitor is None:
            access_monitor = SQLiteAccessMonitor()
        self.access_monitor = access_monitor

    async def create_proxy_for_servers(
        self,
        servers: List[ServerConfig],
        name: Optional[str] = None,
        stdio_mode: bool = True,
        action: str = "proxy",
        profile_name: Optional[str] = None,
    ) -> FastMCP:
        """
        Create a FastMCP proxy that aggregates multiple MCPM servers.

        Args:
            servers: List of ServerConfig objects to aggregate
            name: Optional name for the proxy
            stdio_mode: If True, skip auth middleware (for stdio operations)

        Returns:
            FastMCP proxy instance with MCPM middleware
        """
        if not servers:
            raise ValueError("At least one server must be provided")

        # Create FastMCP server configurations as plain dictionaries
        server_configs: Dict[str, StdioMCPServer | RemoteMCPServer] = {}

        for server in servers:
            # Handle different server transport types with proper type checking
            if isinstance(server, STDIOServerConfig):
                # STDIOServerConfig - command must be a list of strings
                # The command should be a list containing the command and its arguments
                command_parts = [server.command]
                if server.args:
                    command_parts.extend(server.args)

                # Always provide environment variables to trigger FastMCP's os.environ.copy()
                # This fixes a bug where stdio subprocesses get no PATH if env_vars is empty
                env_config = {"MCPM_STDIO_SERVER": "true"}
                if server.env:
                    # Ensure all environment values are strings (server.env is Dict[str, str])
                    env_config.update(server.env)

                server_configs[server.name] = StdioMCPServer(
                    command=server.command,
                    args=server.args or [],
                    env=env_config,
                )
            elif isinstance(server, RemoteServerConfig):
                # RemoteServerConfig - HTTP/SSE transport
                # Convert all header values to strings (FastMCP expects Dict[str, str])
                string_headers = {k: str(v) for k, v in server.headers.items()} if server.headers else {}
                server_configs[server.name] = RemoteMCPServer(
                    url=server.url,
                    headers=string_headers,
                )
            elif isinstance(server, CustomServerConfig):
                # CustomServerConfig is for non-standard client configs - skip it
                # These are client-specific configurations that don't go through the proxy
                continue
            else:
                # Unknown server type
                raise ValueError(f"Server {server.name} has unsupported configuration type: {type(server).__name__}")

        # Check if we have any servers to proxy after filtering
        if not server_configs:
            raise ValueError("No supported servers to proxy (all servers were skipped or unsupported)")

        # Create the proxy configuration dictionary directly
        proxy_config = MCPConfig(mcpServers=server_configs)

        proxy = FastMCP.as_proxy(proxy_config, name=name or "mcpm-aggregated")

        # Add MCPM middleware
        # For single server proxies, use the server name for tracking
        server_name = servers[0].name if len(servers) == 1 else None
        self._add_mcpm_middleware(
            proxy, stdio_mode=stdio_mode, server_name=server_name, action=action, profile_name=profile_name
        )

        return proxy

    async def create_proxy_for_profile(
        self, profile_servers: List[ServerConfig], profile_name: str, stdio_mode: bool = True
    ) -> FastMCP:
        """
        Create a FastMCP proxy for a specific MCPM profile.

        Args:
            profile_servers: List of servers in the profile
            profile_name: Name of the profile
            stdio_mode: If True, skip auth middleware (for stdio operations)

        Returns:
            FastMCP proxy instance configured for the profile
        """
        return await self.create_proxy_for_servers(
            profile_servers, name=f"mcpm-profile-{profile_name}", stdio_mode=stdio_mode
        )

    def _add_mcpm_middleware(
        self,
        proxy: FastMCP,
        stdio_mode: bool = True,
        server_name: Optional[str] = None,
        action: str = "proxy",
        profile_name: Optional[str] = None,
    ) -> None:
        """Add MCPM-specific middleware to the proxy."""

        # Add unified tracking middleware (replaces both monitoring and usage tracking)
        if self.access_monitor:
            transport = SessionTransport.STDIO if stdio_mode else SessionTransport.HTTP
            unified_middleware = MCPMUnifiedTrackingMiddleware(
                access_monitor=self.access_monitor,
                server_name=server_name,
                action=action,
                profile_name=profile_name,
                transport=transport,
            )
            proxy.add_middleware(unified_middleware)

            # Store reference for cleanup
            setattr(proxy, "_mcpm_unified_middleware", unified_middleware)

        # Add authentication middleware (only for HTTP/network operations, not stdio)
        if self.auth_enabled and not stdio_mode and self.api_key:
            proxy.add_middleware(MCPMAuthMiddleware(self.api_key))


async def create_mcpm_proxy(
    servers: List[ServerConfig],
    name: Optional[str] = None,
    auth_enabled: bool = False,
    api_key: Optional[str] = None,
    access_monitor: Optional[AccessMonitor] = None,
    stdio_mode: bool = True,
    action: str = "proxy",
    profile_name: Optional[str] = None,
) -> FastMCP:
    """
    Convenience function to create a FastMCP proxy with MCPM integration.

    Args:
        servers: List of ServerConfig objects to aggregate
        name: Optional name for the proxy
        auth_enabled: Whether authentication is enabled.
        api_key: The API key to use for authentication.
        access_monitor: Optional access monitor
        stdio_mode: If True, skip auth middleware (for stdio operations)

    Returns:
        Configured FastMCP proxy instance
    """
    factory = MCPMProxyFactory(auth_enabled=auth_enabled, api_key=api_key, access_monitor=access_monitor)
    proxy = await factory.create_proxy_for_servers(
        servers, name, stdio_mode=stdio_mode, action=action, profile_name=profile_name
    )

    # Initialize the access monitor if provided
    if access_monitor:
        await access_monitor.initialize_storage()

    return proxy
