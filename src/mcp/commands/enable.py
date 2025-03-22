"""
Enable command for MCP
"""

import click
from rich.console import Console

from mcp.utils.config import ConfigManager
from mcp.utils.server_manager import ServerManager

console = Console()
config_manager = ConfigManager()
server_manager = ServerManager(config_manager)

@click.command()
@click.argument("server_name")
@click.option("--client", required=True, help="Client name to enable the server for")
def enable(server_name, client):
    """Enable an MCP server for a specific client.
    
    Examples:
        mcp enable filesystem --client=claude-desktop
    """
    console.print(f"[bold green]Enabling MCP server:[/] {server_name} for client {client}")
    
    # Check if server exists
    if not config_manager.get_server_info(server_name):
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found. Please install it first.")
        return
    
    # Check if client is valid
    if client not in config_manager.get_config()["clients"]:
        console.print(f"[bold red]Error:[/] Unknown client '{client}'.")
        console.print("Supported clients: " + ", ".join(config_manager.get_config()["clients"].keys()))
        return
    
    # Check if server is already enabled for this client
    client_servers = config_manager.get_client_servers(client)
    if server_name in client_servers:
        console.print(f"[yellow]Server '{server_name}' is already enabled for client '{client}'.[/]")
        return
    
    # Enable the server for this client
    success = config_manager.enable_server_for_client(server_name, client)
    
    if success:
        console.print(f"[bold green]Successfully enabled '{server_name}' for client '{client}'![/]")
    else:
        console.print(f"[bold red]Failed to enable '{server_name}' for client '{client}'.[/]")
