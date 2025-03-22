"""
Disable command for MCP
"""

import click
from rich.console import Console

console = Console()

@click.command()
@click.argument("server_name")
@click.option("--client", required=True, help="Client name to disable the server for")
def disable(server_name, client):
    """Disable an MCP server for a specific client.
    
    Examples:
        mcp disable filesystem --client=claude-desktop
    """
    console.print(f"[bold yellow]Disabling MCP server:[/] {server_name} for client {client}")
    
    # Placeholder for disable functionality
    console.print("[yellow]This functionality will be implemented soon.[/]")
