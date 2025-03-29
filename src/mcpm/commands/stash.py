"""Stash command for MCPM - temporarily stores server configuration aside"""

import logging
import click
from rich.console import Console

from mcpm.utils.client_registry import ClientRegistry
from mcpm.utils.config import ConfigManager

console = Console()
logger = logging.getLogger(__name__)


@click.command()
@click.argument("server_name")
def stash(server_name):
    """Temporarily store a server configuration aside.

    This command disables an active server without removing it, storing its
    configuration for later use. You can restore it with the 'pop' command.

    Examples:
        mcpm stash memory
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

    # Check if the server exists in the active client
    server_config = client_manager.get_server(server_name)
    if not server_config:
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in {client_name}.")
        return

    # Convert ServerConfig to dictionary for storage
    server_data = server_config.to_dict() if hasattr(server_config, "to_dict") else server_config

    # Access the global config manager
    config_manager = ConfigManager()

    # Check if server is already stashed
    if config_manager.is_server_stashed(client, server_name):
        console.print(f"[bold red]Error:[/] Server '{server_name}' is already stashed for {client_name}.")
        return

    # Display server information before stashing
    console.print(f"\n[bold cyan]Stashing server:[/] {server_name}")

    # Store server in global config's stashed_servers
    stash_success = config_manager.stash_server(client, server_name, server_data)

    # Remove the server from the client's configuration
    if stash_success:
        remove_success = client_manager.remove_server(server_name)

        if remove_success:
            console.print(f"[bold yellow]Stashed[/] MCP server '{server_name}' for {client_name}")
            console.print("Server configuration is stored and can be restored with 'mcpm pop'.")
        else:
            # If removing failed, also remove from stashed servers to avoid issues
            config_manager.pop_server(client, server_name)
            console.print(f"[bold red]Failed to remove server from {client_name}. Stashing aborted.")
    else:
        console.print(f"[bold red]Failed to stash[/] '{server_name}' for {client_name}.")
