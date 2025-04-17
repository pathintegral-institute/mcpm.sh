"""
Search command for MCPM - Search and display available MCP servers from the registry
"""

import click
from rich.console import Console

from mcpm.utils.display import print_error, print_servers_table, print_simple_servers_list
from mcpm.utils.repository import RepositoryManager

console = Console()
repo_manager = RepositoryManager()


@click.command()
@click.argument("query", required=False)
@click.option("--table", is_flag=True, help="Display results in table format with descriptions")
@click.help_option("-h", "--help")
def search(query, table=False):
    """Search available MCP servers.

    Searches the MCP registry for available servers. Without arguments, lists all available servers.
    By default, only shows server names. Use --table for more details.

    Examples:

    \b
        mcpm search                  # List all available servers (names only)
        mcpm search github           # Search for github server
        mcpm search --table          # Show results in a table with descriptions
    """
    # Show appropriate search message
    search_criteria = []
    if query:
        search_criteria.append(f"matching '[bold]{query}[/]'")

    if search_criteria:
        console.print(f"[bold green]Searching for MCP servers[/] {' '.join(search_criteria)}")
    else:
        console.print("[bold green]Listing all available MCP servers[/]")

    # Search for servers
    try:
        # Get all matching servers from registry
        servers = repo_manager.search_servers(query)

        # No additional filters in the new architecture

        if not servers:
            console.print("[yellow]No matching MCP servers found.[/]")
            return

        # Show different views based on detail level
        if table:
            print_servers_table(servers)
        else:
            print_simple_servers_list(servers)

        # Show summary count
        console.print(f"\n[green]Found {len(servers)} server(s) matching search criteria[/]")

    except Exception as e:
        print_error("Error searching for servers", str(e))
