"""
Remove command for MCPM
"""

import click
from rich.console import Console
from rich.prompt import Confirm
from rich.markup import escape

from mcpm.utils.client_registry import ClientRegistry

console = Console()


@click.command()
@click.argument("server_name")
@click.option("--force", is_flag=True, help="Force removal without confirmation")
def remove(server_name, force):
    """Remove an installed MCP server.

    Examples:
        mcpm remove filesystem
        mcpm remove filesystem --force
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

    # Actually remove the server from the active client's config
    success = client_manager.remove_server(server_name)

    if success:
        console.print(f"[green]Successfully removed server:[/] {server_name}")
        console.print(f"[italic]Note: {client_name} must be restarted for changes to take effect.[/]")
    else:
        console.print(f"[bold red]Error:[/] Failed to remove server '{server_name}'.")
