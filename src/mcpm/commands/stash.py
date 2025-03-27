"""
Stash command for MCPM - temporarily stores server configuration aside
"""

import click
from rich.console import Console

from mcpm.utils.client_registry import ClientRegistry

console = Console()

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
    server_info = client_manager.get_server(server_name)
    if not server_info:
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in {client_name}.")
        return
    
    # Display server information before stashing
    console.print(f"\n[bold cyan]Stashing server:[/] {server_name}")
    
    # Stash the server (disable it)
    success = client_manager.disable_server(server_name)
    
    if success:
        console.print(f"[bold yellow]Stashed[/] MCP server '{server_name}' for {client_name}")
        console.print("Server configuration is stored and can be restored with 'mcpm pop'.")
    else:
        console.print(f"[bold red]Failed to stash[/] '{server_name}' for {client_name}.")
