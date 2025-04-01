"""
Main router class that coordinates client and server handlers.
Acts as the central component for the MCPM router.
"""

import asyncio
import logging
from typing import Any, Dict, List, Tuple

from .client_handler import ClientHandler
from .connection_manager import ConnectionManager
from .connection_types import ConnectionDetails
from .server_handler import ServerHandler

log = logging.getLogger(__name__)


class MCPRouter:
    """
    Main router class that coordinates the connection between upstream clients
    and downstream servers. It provides the main API for the application.
    """

    def __init__(self, client_info: Any):
        """
        Initialize the router with the necessary handlers.

        Args:
            client_info: The client info to use when connecting to downstream servers
        """
        self.connection_manager = ConnectionManager()
        self.server_handler = ServerHandler(self.connection_manager, client_info)
        self.client_handler = ClientHandler(self.connection_manager)

        # Set up callback for forwarding notifications from servers to clients
        self.server_handler.set_upstream_notify_callback(self.client_handler.broadcast_notification)

    async def connect_to_downstream(self, server_id: str, connection_details: ConnectionDetails) -> asyncio.Task:
        """
        Connect to a downstream server.

        Args:
            server_id: Unique identifier for the server
            connection_details: Connection details for the server

        Returns:
            Task managing the server connection
        """
        log.info(f"Router connecting to downstream server: {server_id}")
        # Create a task for the connection to run in the background
        task = asyncio.create_task(self.server_handler.connect_to_server(server_id, connection_details))
        return task

    async def disconnect_from_downstream(self, server_id: str):
        """
        Disconnect from a downstream server.

        Args:
            server_id: Unique identifier for the server
        """
        log.info(f"Router disconnecting from downstream server: {server_id}")
        await self.server_handler.disconnect_from_server(server_id)

    async def start_client_server(self, host: str = "127.0.0.1", port: int = 8765):
        """
        Start the SSE server for upstream clients.

        Args:
            host: Host to bind the server to
            port: Port to bind the server to
        """
        log.info(f"Starting client-facing SSE server on {host}:{port}")
        # This will start the SSE server and keep it running
        await self.client_handler.start_sse_server(host, port)

    def get_aggregated_capabilities(self, capability_type: str) -> List[Dict[str, Any]]:
        """
        Get aggregated capabilities of a specific type from all connected servers.

        Args:
            capability_type: Type of capabilities to get (tools, resources, prompts)

        Returns:
            List of capability schemas
        """
        return self.server_handler.get_aggregated_capabilities_list(capability_type)

    def get_connected_servers(self) -> List[str]:
        """
        Get a list of connected server IDs.

        Returns:
            List of server IDs
        """
        return list(self.connection_manager.get_downstream_servers().keys())

    def namespace_id(self, server_id: str, original_id: str) -> str:
        """
        Create a namespaced ID by combining server ID and original ID.

        Args:
            server_id: ID of the server
            original_id: Original ID of the resource/tool/prompt

        Returns:
            Namespaced ID
        """
        return f"{server_id}/{original_id}"

    def denamespace_id(self, namespaced_id: str) -> Tuple[str, str]:
        """
        Split a namespaced ID into server ID and original ID.

        Args:
            namespaced_id: Combined ID in the format "server_id/original_id"

        Returns:
            Tuple of (server_id, original_id)
        """
        parts = namespaced_id.split("/", 1)
        if len(parts) != 2:
            log.error(f"Invalid namespaced ID format: {namespaced_id}")
            raise ValueError(f"Invalid namespaced ID format: {namespaced_id}")
        return parts[0], parts[1]
