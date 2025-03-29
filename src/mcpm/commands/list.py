"""
List command for MCP
"""

import click
from rich.console import Console
from rich.table import Table
from rich.markup import escape

from mcpm.utils.client_registry import ClientRegistry

console = Console()


@click.command(name="list")
def list():
    """List all installed MCP servers.

    Examples:
        mcpm list
    """
    # Get the active client manager and information
    client_manager = ClientRegistry.get_active_client_manager()
    client = ClientRegistry.get_active_client()
    client_info = ClientRegistry.get_client_info(client)
    client_name = client_info.get("name", client)

    # Check if client is supported
    if client_manager is None:
        console.print("[bold red]Error:[/] Unsupported active client")
        console.print("Please switch to a supported client using 'mcpm client <client-name>'")
        return

    console.print(f"[bold green]MCP servers installed in {client_name}:[/]")

    # Get all servers from active client config
    servers = client_manager.get_servers()

    if not servers:
        console.print(f"[yellow]No MCP servers found in {client_name}.[/]")
        console.print("Use 'mcpm add <server>' to add a server.")
        return

    # Count the configured servers
    server_count = len(servers)
    console.print(f"[bold]Configured servers:[/] {server_count}\n")

    # Display detailed information for each server
    for server_name, server_info in servers.items():
        # Server name and command
        console.print(f"[bold cyan]{server_name}[/]")
        command = server_info.get("command", "N/A")
        console.print(f"  Command: [green]{command}[/]")

        # Display arguments
        args = server_info.get("args", [])
        if args:
            console.print("  Arguments:")
            for i, arg in enumerate(args):
                console.print(f"    {i}: [yellow]{escape(arg)}[/]")

            # Get package name (usually the second argument)
            if len(args) > 1:
                console.print(f"  Package: [magenta]{args[1]}[/]")

        # Display environment variables
        env_vars = server_info.get("env", {})
        if env_vars:
            console.print("  Environment Variables:")
            for key, value in env_vars.items():
                console.print(f'    [bold blue]{key}[/] = [green]"{value}"[/]')
        else:
            console.print("  Environment Variables: [italic]None[/]")

        # Add a separator line between servers
        console.print("  " + "-" * 50)
