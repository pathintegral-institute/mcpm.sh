"""Pop command for MCPM - restores previously stashed server configuration"""

import logging

import click
from rich.console import Console

from mcpm.clients.client_config import ClientConfigManager
from mcpm.utils.client_registry import ClientRegistry

console = Console()
logger = logging.getLogger(__name__)
client_config_manager = ClientConfigManager()


@click.command()
@click.argument("server_name")
def pop(server_name):
    """Restore a previously stashed server configuration.

    This command re-enables a previously stashed (disabled) server,
    restoring it to active status.

    Examples:
        mcpm pop memory
    """
    # Get the active client manager and related information
    client_manager = ClientRegistry.get_active_client_manager()
    client = ClientRegistry.get_active_client()
    client_info = ClientRegistry.get_client_info(client)
    client_name = client_info.get("name", client)

    # Check if client is supported
    if client_manager is None:
        console.print("[bold red]Error:[/] Unsupported active client")
        console.print("Please switch to a supported client using 'mcpm client <client-name>'")
        return

    # Check if the server is stashed for this client
    if not client_config_manager.is_server_stashed(client, server_name):
        console.print(
            f"[bold red]Error:[/] Server '{server_name}' not found in stashed configurations for {client_name}."
        )
        return

    # Get the server configuration from global stashed servers
    server_data = client_config_manager.pop_server(client, server_name)
    if not server_data:
        console.print(f"[bold red]Error:[/] Failed to retrieve stashed configuration for server '{server_name}'.")
        return

    # Convert the server configuration to the client's format and add it back
    # to the active servers
    server_config = client_manager.from_client_format(server_name, server_data)
    success = client_manager.add_server(server_config)

    if success:
        console.print(f"[bold green]Restored[/] MCP server '{server_name}' for {client_name}")
        console.print("Remember to restart the client for changes to take effect.")
    else:
        # If adding failed, re-stash the server to avoid data loss
        client_config_manager.stash_server(client, server_name, server_data)
        console.print(f"[bold red]Failed to restore[/] '{server_name}' for {client_name}.")
