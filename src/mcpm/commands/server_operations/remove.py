"""
Remove command for MCPM
"""

import click
from rich.console import Console
from rich.markup import escape
from rich.prompt import Confirm

from mcpm.commands.server_operations.common import (
    client_get_server,
    client_remove_server,
    determine_target,
    profile_get_server,
    profile_remove_server,
)
from mcpm.utils.scope import ScopeType

console = Console()


@click.command()
@click.argument("server_name")
@click.option("--force", is_flag=True, help="Force removal without confirmation")
@click.help_option("-h", "--help")
def remove(server_name, force):
    """Remove an installed MCP server.

    Examples:

    \b
        mcpm rm filesystem
        mcpm rm @cursor/filesystem
        mcpm rm %profile/filesystem
        mcpm rm filesystem --force
    """
    scope_type, scope, server_name = determine_target(server_name)
    if not scope_type or not scope or not server_name:
        return

    if scope_type == ScopeType.CLIENT:
        # Get the active client manager and related information
        server_info = client_get_server(scope, server_name)
        if not server_info:
            console.print(f"[bold red]Error:[/] Server '{server_name}' not found in {scope}.")
            return
    else:
        # Get the active profile manager and information
        server_info = profile_get_server(scope, server_name)
        if not server_info:
            console.print(f"[bold red]Error:[/] Server '{server_name}' not found in profile '{scope}'.")
            return

    # Display server information before removal
    console.print(f"\n[bold cyan]Server information for:[/] {server_name}")

    # Server command
    command = getattr(server_info, "command", "N/A")
    console.print(f"  Command: [green]{command}[/]")

    # Display arguments
    args = getattr(server_info, "args", [])
    if args:
        console.print("  Arguments:")
        for i, arg in enumerate(args):
            console.print(f"    {i}: [yellow]{escape(arg)}[/]")

        # Get package name (usually the second argument)
        if len(args) > 1:
            console.print(f"  Package: [magenta]{args[1]}[/]")

    # Display environment variables
    env_vars = getattr(server_info, "env", {})
    if env_vars and len(env_vars) > 0:
        console.print("  Environment Variables:")
        for key, value in env_vars.items():
            console.print(f'    [bold blue]{key}[/] = [green]"{value}"[/]')
    else:
        console.print("  Environment Variables: [italic]None[/]")

    console.print("  " + "-" * 50)

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
    console.print(f"[bold red]Removing MCP server:[/] {server_name}")

    if scope_type == ScopeType.CLIENT:
        # Actually remove the server from the active client's config
        success = client_remove_server(scope, server_name)
    else:
        # Actually remove the server from the active profile's config
        success = profile_remove_server(scope, server_name)

    if success:
        console.print(f"[green]Successfully removed server:[/] {server_name}")
    else:
        console.print(f"[bold red]Error:[/] Failed to remove server '{server_name}'.")
