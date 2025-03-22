"""
Update command for MCP
"""

import click
from rich.console import Console

console = Console()

@click.command()
@click.argument("server_name", required=False)
def update(server_name):
    """Update installed servers or a specific server.
    
    Examples:
        mcp update
        mcp update filesystem
    """
    if server_name:
        console.print(f"[bold green]Updating MCP server:[/] {server_name}")
    else:
        console.print("[bold green]Updating all installed MCP servers[/]")
        
    # Placeholder for update functionality
    console.print("[yellow]This functionality will be implemented soon.[/]")
