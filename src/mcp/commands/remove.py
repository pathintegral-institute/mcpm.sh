"""
Remove command for MCP
"""

import click
from rich.console import Console
from rich.prompt import Confirm

from mcp.clients.claude_desktop import ClaudeDesktopManager
from mcp.clients.windsurf import WindsurfManager
from mcp.utils.config import ConfigManager

console = Console()
config_manager = ConfigManager()
claude_manager = ClaudeDesktopManager()
windsurf_manager = WindsurfManager()

@click.command()
@click.argument("server_name")
@click.option("--force", is_flag=True, help="Force removal without confirmation")
def remove(server_name, force):
    """Remove an installed MCP server.
    
    Examples:
        mcp remove filesystem
        mcp remove filesystem --force
    """
    # Get the active client and its corresponding manager
    active_client = config_manager.get_active_client()
    
    # Select appropriate client manager based on active client
    if active_client == "claude-desktop":
        client_manager = claude_manager
        client_name = "Claude Desktop"
    elif active_client == "windsurf":
        client_manager = windsurf_manager
        client_name = "Windsurf"
    else:
        console.print(f"[bold red]Error:[/] Unsupported active client: {active_client}")
        console.print("Please switch to a supported client using 'mcp client <client-name>'")
        return
    
    # Check if the server exists in the active client
    server_info = client_manager.get_server(server_name)
    if not server_info:
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in {client_name}.")
        return
    
    # Get confirmation if --force is not used
    if not force:
        console.print(f"[bold yellow]Are you sure you want to remove:[/] {server_name}")
        console.print("[italic]To bypass this confirmation, use --force[/]")
        # Use Rich's Confirm for a better user experience
        confirmed = Confirm.ask("Proceed with removal?")
        if not confirmed:
            console.print("Removal cancelled.")
            return
    
    # Log the removal action
    console.print(f"[bold red]Removing MCP server:[/] {server_name}")
    
    # Actually remove the server from the active client's config
    success = client_manager.remove_server(server_name)
    
    if success:
        console.print(f"[green]Successfully removed server:[/] {server_name}")
        console.print(f"[italic]Note: {client_name} must be restarted for changes to take effect.[/]")
    else:
        console.print(f"[bold red]Error:[/] Failed to remove server '{server_name}'.")
