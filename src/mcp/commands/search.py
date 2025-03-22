"""
Search command for MCP
"""

import click
from rich.console import Console
from rich.table import Table

from mcp.utils.repository import RepositoryManager

console = Console()
repo_manager = RepositoryManager()

@click.command()
@click.argument("query", required=False)
@click.option("--tags", help="Search servers by tag")
def search(query, tags):
    """Search available MCP servers.
    
    Examples:
        mcp search
        mcp search filesystem
        mcp search --tags=file
    """
    if tags:
        console.print(f"[bold green]Searching for MCP servers with tag:[/] {tags}")
    elif query:
        console.print(f"[bold green]Searching for MCP servers matching:[/] {query}")
    else:
        console.print("[bold green]Listing all available MCP servers[/]")
    
    # Search for servers
    try:
        servers = repo_manager.search_servers(query, tags)
        
        if not servers:
            console.print("[yellow]No matching MCP servers found.[/]")
            return
        
        # Display results in a table
        table = Table(show_header=True, header_style="bold")
        table.add_column("Name")
        table.add_column("Version")
        table.add_column("Description")
        table.add_column("Tags")
        table.add_column("Supported Clients")
        
        for server in servers:
            table.add_row(
                server["name"],
                server["version"],
                server["description"],
                ", ".join(server["tags"]),
                ", ".join(server["clients"])
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[bold red]Error searching for servers:[/] {str(e)}")

