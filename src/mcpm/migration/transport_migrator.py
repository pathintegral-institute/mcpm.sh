"""
Migration utility for switching from SSE to Streamable HTTP transport
"""

import logging

from rich.console import Console

from mcpm.clients.client_registry import ClientRegistry

logger = logging.getLogger(__name__)
console = Console()


class TransportMigrator:
    """Migrates client configurations from SSE to Streamable HTTP"""

    def __init__(self):
        self.registry = ClientRegistry()

    def migrate_all_clients(self) -> bool:
        """
        Migrate all detected client configurations

        Returns:
            bool: True if any changes were made
        """
        changes_made = False
        console.print("[bold cyan]Checking clients for SSE configuration...[/]")

        managers = self.registry.get_all_client_managers()

        for name, manager in managers.items():
            if not manager.is_client_installed():
                # Skip uninstalled clients to avoid creating noise/files
                continue

            try:
                # Access private _load_config / _save_config if available,
                # or we might need to implement public methods in BaseClientManager if they don't exist.
                # BaseClientManager has _load_config and _save_config but they are protected.
                # We'll use them carefully or add a public method.

                # Actually, let's check if we can add a method to BaseClientManager or just use the protected ones.
                # Python allows access.

                config = manager._load_config()
                if not config:
                    continue

                server_key = getattr(manager, "configure_key_name", "mcpServers")

                # Handle nested structure for VSCode
                servers_container = config
                if name == "vscode":
                    if "mcp" not in config:
                        continue
                    if "servers" not in config["mcp"]:
                        continue
                    servers_container = config["mcp"]
                    server_key = "servers"

                if server_key not in servers_container:
                    continue

                servers = servers_container[server_key]
                client_updated = False

                for server_name, server_config in servers.items():
                    if not isinstance(server_config, dict):
                        continue

                    # Update transport
                    if server_config.get("transport") == "sse":
                        server_config["transport"] = "streamable-http"
                        client_updated = True

                    # Update URL
                    url = server_config.get("url", "")
                    if "/sse" in url:
                        # Replace /sse/ or /sse with /mcp/ or /mcp
                        new_url = url.replace("/sse/", "/mcp/").replace("/sse", "/mcp")
                        if url != new_url:
                            server_config["url"] = new_url
                            client_updated = True

                if client_updated:
                    manager._save_config(config)
                    console.print(f"  ✅ Updated [green]{manager.display_name}[/]")
                    changes_made = True
                else:
                    logger.debug(f"No SSE config found for {name}")

            except Exception as e:
                console.print(f"  ❌ Error checking {name}: {e}")

        return changes_made
