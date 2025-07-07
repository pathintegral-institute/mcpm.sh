"""
Remove command for MCPM
"""

from rich.console import Console
from rich.prompt import Confirm

from mcpm.commands.target_operations.common import (
    determine_target,
    global_get_server,
    global_remove_server,
)
from mcpm.utils.display import print_server_config
from mcpm.utils.rich_click_config import click

console = Console()


@click.command()
@click.argument("server_name")
@click.option("--force", "-f", is_flag=True, help="Force removal without confirmation")
@click.help_option("-h", "--help")
def remove(server_name, force):
    """Remove an installed MCP server from global configuration.

    Removes servers from the global MCPM configuration and clears
    any profile tags associated with the server.

    Examples:

    \b
        mcpm rm filesystem
        mcpm rm filesystem --force
    """
    # v2.0: Extract server name and use global configuration
    scope_type, scope, extracted_server_name = determine_target(server_name)

    # In v2.0, we use the extracted server name, or the original if no extraction occurred
    actual_server_name = extracted_server_name if extracted_server_name else server_name

    # Get server from global configuration
    server_info = global_get_server(actual_server_name)
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
    console.print(f"[bold red]Removing MCP server from global configuration:[/] {actual_server_name}")

    # v2.0: Remove from global configuration
    success = global_remove_server(actual_server_name)

    if success:
        console.print(f"[green]Successfully removed server:[/] {actual_server_name}")
        console.print("[dim]Note: Server has been removed from global config. Profile tags are also cleared.[/]")
    else:
        console.print(f"[bold red]Error:[/] Failed to remove server '{actual_server_name}'.")
