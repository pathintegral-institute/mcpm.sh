"""
Pop command for MCPM - restores previously stashed server configuration
"""

import click
from rich.console import Console

from mcpm.utils.client_manager import get_active_client_info

console = Console()

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
    client_manager, client_name, client_id = get_active_client_info()
    
    # Check if client is supported
    if client_manager is None:
        console.print("[bold red]Error:[/] Unsupported active client")
        console.print("Please switch to a supported client using 'mcpm client <client-name>'")
        return
    
    # Check if the server exists in the stashed configurations
    if not client_manager.is_server_disabled(server_name):
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in stashed configurations.")
        return
    
    # Pop (re-enable) the server
    success = client_manager.enable_server(server_name)
    
    if success:
        console.print(f"[bold green]Restored[/] MCP server '{server_name}' for {client_name}")
        console.print("Remember to restart the client for changes to take effect.")
    else:
        console.print(f"[bold red]Failed to restore[/] '{server_name}' for {client_name}.")
