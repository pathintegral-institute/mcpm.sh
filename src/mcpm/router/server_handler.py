"""
Handles outgoing connections to downstream MCP servers.
Acts as the client-facing part of the aggregator.
"""

from typing import Any, Dict  # Removed List

from .connection_manager import ConnectionManager


class ServerHandler:
    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager
        self.aggregated_capabilities: Dict[str, Dict] = {"tools": {}, "resources": {}, "prompts": {}}
        pass

    async def connect_to_server(self, server_id: str, connection_details: Any):
        """Establishes a connection to a downstream MCP server."""
        # TODO: Implement client connection logic
        # (e.g., using StdioClientTransport or SSEClientTransport)
        # TODO: After connection and initialization, fetch capabilities
        print(f"Attempting to connect to downstream server: {server_id}")
        # Placeholder: Assume connection successful and add to manager
        # downstream_client = ...  # Actual client instance
        # self.connection_manager.add_downstream_server(
        #     server_id, downstream_client
        # )
        # await self._fetch_and_aggregate_capabilities(
        #     server_id, downstream_client
        # )
        pass

    async def disconnect_from_server(self, server_id: str):
        """Disconnects from a downstream MCP server."""
        # TODO: Implement client disconnection logic
        print(f"Disconnecting from downstream server: {server_id}")
        # TODO: Remove server's capabilities from aggregation
        self.connection_manager.remove_downstream_server(server_id)
        self._remove_server_capabilities(server_id)
        pass

    async def _fetch_and_aggregate_capabilities(self, server_id: str, client: Any):
        """Fetches capabilities from a connected server and adds them to the aggregate pool."""
        print(f"Fetching capabilities from {server_id}...")
        try:
            # Replace with actual client calls
            # tools_resp = await client.listTools()
            # resources_resp = await client.listResources()
            # prompts_resp = await client.listPrompts()
            tools_resp = {"tools": []}  # Placeholder
            resources_resp = {"resources": []}  # Placeholder
            prompts_resp = {"prompts": []}  # Placeholder

            # TODO: Properly use these later
            _ = resources_resp
            _ = prompts_resp

            for tool in tools_resp.get("tools", []):
                # Namespace the ID
                tool_id = f"{server_id}/{tool['id']}"
                self.aggregated_capabilities["tools"][tool_id] = {
                    **tool,
                    "original_id": tool["id"],
                    "server_id": server_id,
                }

            # TODO: Aggregate resources and prompts similarly

            print(f"Successfully aggregated capabilities from {server_id}")
            # TODO: Notify upstream clients about the updated capabilities list?
        except Exception as e:
            print(f"Error fetching capabilities from {server_id}: {e}")

    def _remove_server_capabilities(self, server_id: str):
        """Removes capabilities associated with a disconnected server."""
        tools = self.aggregated_capabilities["tools"]
        self.aggregated_capabilities["tools"] = {k: v for k, v in tools.items() if v["server_id"] != server_id}
        # TODO: Remove resources and prompts similarly
        print(f"Removed capabilities for {server_id}")

    def get_aggregated_capabilities(self) -> Dict[str, Dict]:
        """Returns the current aggregated capabilities."""
        return self.aggregated_capabilities

    async def route_request(self, request: Dict):
        """Routes an incoming request from an upstream client to the correct downstream server."""
        # TODO: Implement routing logic based on namespaced ID
        # 1. Parse request (e.g., method, params like tool_id)
        # 2. Extract server_id and original_id from namespaced ID
        # 3. Get the correct downstream server client from connection_manager
        # 4. Forward the request with the original_id
        # 5. Map request IDs for response routing
        print(f"Routing request: {request.get('method')}")
        pass
