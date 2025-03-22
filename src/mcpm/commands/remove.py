"""
Remove command for MCPM
"""

import click
from rich.console import Console
from rich.prompt import Confirm

from mcpm.utils.claude_desktop import ClaudeDesktopManager

console = Console()
claude_manager = ClaudeDesktopManager()

@click.command()
@click.argument("server_name")
@click.option("--force", is_flag=True, help="Force removal without confirmation")
def remove(server_name, force):
    """Remove an installed MCP server.
    
    Examples:
        mcpm remove filesystem
        mcpm remove filesystem --force
    """
    # Check if the server exists in Claude Desktop
    server_info = claude_manager.get_server(server_name)
    if not server_info:
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in Claude Desktop.")
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
    
    # Actually remove the server from Claude Desktop config
    success = claude_manager.remove_server(server_name)
    
    if success:
        console.print(f"[green]Successfully removed server:[/] {server_name}")
        console.print("[italic]Note: Claude Desktop must be restarted for changes to take effect.[/]")
    else:
        console.print(f"[bold red]Error:[/] Failed to remove server '{server_name}'.")
