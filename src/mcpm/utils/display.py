"""
Utility functions for displaying MCP server configurations
"""

from rich.console import Console
from rich.markup import escape
from rich.table import Table

console = Console()


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


def print_error(message, details=None):
    """Print a standardized error message.

    Args:
        message: The main error message
        details: Optional additional error details
    """
    console.print(f"[bold red]Error:[/] {message}")
    if details:
        console.print(f"[red]{details}[/]")


def print_client_error(client_name):
    """Print a standardized client-related error message.

    Args:
        client_name: Name of the client that caused the error
    """
    console.print("[bold red]Error:[/] Unsupported active client")
    console.print("Please switch to a supported client using 'mcpm client <client-name>'")
