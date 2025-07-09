"""
Uninstall command for removing MCP servers from global configuration
"""

from rich.console import Console
from rich.prompt import Confirm

from mcpm.global_config import GlobalConfigManager
from mcpm.utils.display import print_server_config
from mcpm.utils.rich_click_config import click

console = Console()
global_config_manager = GlobalConfigManager()


def global_get_server(server_name: str):
    """Get a server from the global MCPM configuration."""
    server = global_config_manager.get_server(server_name)
    if not server:
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in global configuration.")
    return server


def global_remove_server(server_name: str) -> bool:
    """Remove a server from the global MCPM configuration and clean up profile tags."""
    if not global_config_manager.server_exists(server_name):
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in global configuration.")
        return False

    # Remove from global config (this automatically removes all profile tags)
    success = global_config_manager.remove_server(server_name)
    return success


@click.command()
@click.argument("server_name")
@click.option("--force", "-f", is_flag=True, help="Force removal without confirmation")
@click.help_option("-h", "--help")
def uninstall(server_name, force):
    """Remove an installed MCP server from global configuration.

    Removes servers from the global MCPM configuration and clears
    any profile tags associated with the server.

    Examples:

    \b
        mcpm uninstall filesystem
        mcpm uninstall filesystem --force
    """
    # Get server from global configuration
    server_info = global_get_server(server_name)
    if not server_info:
        return  # Error message already printed by global_get_server

    # Display server information before removal
    console.print(f"\n[bold cyan]Server information for:[/] {server_name}")

    print_server_config(server_info)

    # Get confirmation if --force is not used
    if not force:
        console.print(f"\n[bold yellow]Are you sure you want to remove:[/] {server_name}")
        console.print("[italic]To bypass this confirmation, use --force[/]")
        # Use Rich's Confirm for a better user experience
        confirmed = Confirm.ask("Proceed with removal?")
        if not confirmed:
            console.print("Removal cancelled.")
            return

    # Log the removal action
    console.print(f"[bold red]Removing MCP server from global configuration:[/] {server_name}")

    # Remove from global configuration
    success = global_remove_server(server_name)

    if success:
        console.print(f"[green]Successfully removed server:[/] {server_name}")
        console.print("[dim]Note: Server has been removed from global config. Profile tags are also cleared.[/]")
    else:
        console.print(f"[bold red]Error:[/] Failed to remove server '{server_name}'.")
