"""
Utility class to track active upstream and downstream connections.
"""

from typing import Any, Dict, List


class ConnectionManager:
    def __init__(self):
        # Using Any for now, replace with actual transport/client types later
        self.upstream_clients: Dict[str, Any] = {}
        self.downstream_servers: Dict[str, Any] = {}
        pass

    def add_upstream_client(self, client_id: str, client_transport: Any):
        self.upstream_clients[client_id] = client_transport
        print(f"Upstream client connected: {client_id}")

    def remove_upstream_client(self, client_id: str):
        if client_id in self.upstream_clients:
            del self.upstream_clients[client_id]
            print(f"Upstream client disconnected: {client_id}")

    def add_downstream_server(self, server_id: str, server_client: Any):
        self.downstream_servers[server_id] = server_client
        print(f"Connected to downstream server: {server_id}")

    def remove_downstream_server(self, server_id: str):
        if server_id in self.downstream_servers:
            del self.downstream_servers[server_id]
            print(f"Disconnected from downstream server: {server_id}")

    def get_upstream_client(self, client_id: str) -> Any:
        return self.upstream_clients.get(client_id)

    def get_downstream_server(self, server_id: str) -> Any:
        return self.downstream_servers.get(server_id)

    def list_upstream_clients(self) -> List[str]:
        return list(self.upstream_clients.keys())

    def list_downstream_servers(self) -> List[str]:
        return list(self.downstream_servers.keys())
