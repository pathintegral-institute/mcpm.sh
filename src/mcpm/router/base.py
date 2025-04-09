from typing import Any, Dict, List, Protocol

from .connection_types import ConnectionDetails


class MCPRouterProtocol(Protocol):
    """Protocol defining the interface that MCPRouter exposes to other components."""

    server_sessions: Dict[str, Any]

    async def add_server(self, server_id: str, connection: ConnectionDetails) -> None:
        """Add a server to the router."""
        ...

    async def remove_server(self, server_id: str) -> None:
        """Remove a server from the router."""
        ...

    async def update_servers(self, connections: List[ConnectionDetails]) -> None:
        """Update the servers based on the configuration."""
        ...
