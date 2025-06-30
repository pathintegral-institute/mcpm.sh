"""
Utility functions for displaying MCP server configurations
"""

import json

from rich.console import Console
from rich.markup import escape
from rich.table import Table

from mcpm.core.schema import CustomServerConfig, RemoteServerConfig, ServerConfig
from mcpm.utils.scope import CLIENT_PREFIX, PROFILE_PREFIX

console = Console()


def print_server_config(server_config: ServerConfig, is_stashed=False):
    """Print detailed information about a server configuration.

    Args:
        server_config: Server configuration information
        is_stashed: Whether the server is stashed (affects display style)
    """
    # Server name and command
    if is_stashed:
        console.print(f"[bold yellow]{server_config.name}[/] [dim](stashed)[/]")
    else:
        console.print(f"[bold cyan]{server_config.name}[/]")

    if isinstance(server_config, RemoteServerConfig):
        console.print(f"  Url: [green]{server_config.url}[/]")
        headers = server_config.headers
        if headers:
            console.print("  Headers:")
            for key, value in headers.items():
                console.print(f'    [bold blue]{key}[/] = [green]"{value}"[/]')
        console.print("  " + "-" * 50)
        return
    if isinstance(server_config, CustomServerConfig):
        console.print("  Type: [green]Custom[/]")
        console.print("  " + "-" * 50)
        console.print("  Config:")
        console.print(json.dumps(server_config.config, indent=2))
        console.print("  " + "-" * 50)
        return
    command = server_config.command
    console.print(f"  Command: [green]{command}[/]")

    # Display arguments
    args = server_config.args
    if args:
        console.print("  Arguments:")
        for i, arg in enumerate(args):
            console.print(f"    {i}: [yellow]{escape(arg)}[/]")

    # Display environment variables
    env_vars = server_config.env
    if env_vars:
        console.print("  Environment Variables:")
        for key, value in env_vars.items():
            console.print(f'    [bold blue]{key}[/] = [green]"{value}"[/]')
    else:
        console.print("  Environment Variables: [italic]None[/]")

    # Add a separator line between servers
    console.print("  " + "-" * 50)


def print_servers_table(servers):
    """Display a formatted table of server information.

    Args:
        servers: List of server dictionaries containing server information
    """
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Categories/Tags", overflow="fold")

    for server in sorted(servers, key=lambda s: s["name"]):
        # Get server data
        name = server["name"]
        display_name = server.get("display_name", name)
        description = server.get("description", "No description")

        # Build categories and tags
        categories = server.get("categories", [])
        tags = server.get("tags", [])
        meta_info = ", ".join([f"[dim]{c}[/]" for c in categories] + [f"[dim]{t}[/]" for t in tags])

        # Add row to table
        table.add_row(f"{display_name}\n[dim]({name})[/]", description, meta_info)

    console.print(table)


def print_simple_servers_list(servers):
    """Display a simple list of server names.

    Args:
        servers: List of server dictionaries containing server information
    """
    # Sort servers by name for consistent display
    sorted_servers = sorted(servers, key=lambda s: s["name"])

    # Format and print each server name
    for server in sorted_servers:
        name = server["name"]
        console.print(f"[cyan]{name}[/]")


def print_error(message, details=None):
    """Print a standardized error message.

    Args:
        message: The main error message
        details: Optional additional error details
    """
    console.print(f"[bold red]Error:[/] {message}")
    if details:
        console.print(f"[red]{details}[/]")


def print_client_error():
    """Print a standardized client-related error message."""
    console.print("[bold red]Error:[/] Unsupported active client")
    console.print("Please switch to a supported client using 'mcpm target set @<client-name>'")


def print_active_scope(scope: str):
    """Display the active client or profile."""
    if scope.startswith(CLIENT_PREFIX):
        console.print(f"[bold green]Working on Active Client:[/] {scope[1:]}\n")
    elif scope.startswith(PROFILE_PREFIX):
        console.print(f"[bold green]Working on Active Profile:[/] {scope[1:]}\n")
    else:
        console.print(f"[bold red]Error:[/] Invalid active scope: {scope}\n")


def print_no_active_scope():
    console.print("[bold red]Error:[/] No active client or profile found.\n")
    console.print("Please set an active target with 'mcpm target set @<client>' or 'mcpm target set %<profile>'.")
