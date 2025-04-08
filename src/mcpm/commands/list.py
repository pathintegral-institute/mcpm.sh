"""
List command for MCP
"""

import click
from rich.console import Console
from rich.markup import escape

from mcpm.clients.client_config import ClientConfigManager
from mcpm.clients.client_registry import ClientRegistry
from mcpm.utils.display import print_server_config

console = Console()
client_config_manager = ClientConfigManager()


def print_server_config(server_name, server_info, is_stashed=False):
    """Print detailed information about a server configuration.

    Args:
        server_name: Name of the server
        server_info: Server configuration information
        is_stashed: Whether the server is stashed (affects display style)
    """
    # Server name and command
    if is_stashed:
        console.print(f"[bold yellow]{server_name}[/] [dim](stashed)[/]")
    else:
        console.print(f"[bold cyan]{server_name}[/]")

    command = server_info.get("command", "N/A")
    console.print(f"  Command: [green]{command}[/]")

    # Display arguments
    args = server_info.get("args", [])
    if args:
        console.print("  Arguments:")
        for i, arg in enumerate(args):
            console.print(f"    {i}: [yellow]{escape(arg)}[/]")

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

    # Get stashed servers
    stashed_servers = client_config_manager.get_stashed_servers(client)

    if not servers and not stashed_servers:
        console.print(f"[yellow]No MCP servers found in {client_name}.[/]")
        console.print("Use 'mcpm add <server>' to add a server.")
        return

    # Count the configured servers
    server_count = len(servers)
    stashed_count = len(stashed_servers)

    # Print active servers
    if servers:
        console.print("\n[bold]Active Servers:[/]")
        for server_name, server_info in servers.items():
            print_server_config(server_name, server_info)

    # Print stashed servers
    if stashed_servers:
        console.print("\n[bold]Stashed Servers:[/]")
        for server_name, server_info in stashed_servers.items():
            print_server_config(server_name, server_info, is_stashed=True)
