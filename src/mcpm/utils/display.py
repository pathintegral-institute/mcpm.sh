"""
Utility functions for displaying MCP server configurations
"""

from rich.console import Console
from rich.markup import escape

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
