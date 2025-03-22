"""
Toggle command for MCP - enables or disables an MCP server
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
@click.option("--client", required=False, help="Client name to toggle the server for (defaults to active client)")
def toggle(server_name, client):
    """Toggle an MCP server on or off for a client.
    
    This command enables a disabled server or disables an enabled server.
    Disabled servers are stored in the MCP configuration and can be re-enabled later.
    
    Examples:
        mcp toggle memory              # Toggle for active client
        mcp toggle memory --client=claude-desktop
    """
    # Use active client if not specified
    if not client:
        client = config_manager.get_active_client()
        console.print(f"Using active client: [cyan]{client}[/]")
    
    # Check if client is valid
    if client not in config_manager.get_config()["clients"]:
        console.print(f"[bold red]Error:[/] Unknown client '{client}'.")
        console.print("Supported clients: " + ", ".join(config_manager.get_config()["clients"].keys()))
        return
    
    # Check if server exists
    if not config_manager.get_server_info(server_name):
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found. Please install it first.")
        return
    
    # Check if server is currently enabled for this client
    client_servers = config_manager.get_client_servers(client)
    is_enabled = server_name in client_servers
    
    if is_enabled:
        # Disable the server for this client
        success = config_manager.disable_server_for_client(server_name, client)
        
        if success:
            console.print(f"[bold yellow]Disabled[/] MCP server '{server_name}' for client '{client}'")
            console.print("Server configuration is stored in MCP and can be re-enabled later.")
        else:
            console.print(f"[bold red]Failed to disable[/] '{server_name}' for client '{client}'.")
    else:
        # Enable the server for this client
        success = config_manager.enable_server_for_client(server_name, client)
        
        if success:
            console.print(f"[bold green]Enabled[/] MCP server '{server_name}' for client '{client}'")
            console.print("Remember to restart the client for changes to take effect.")
        else:
            console.print(f"[bold red]Failed to enable[/] '{server_name}' for client '{client}'.")
