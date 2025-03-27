"""
Search command for MCPM - Search and display available MCP servers from the registry
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from mcpm.utils.repository import RepositoryManager
from mcpm.utils.config import ConfigManager

console = Console()
repo_manager = RepositoryManager()
config_manager = ConfigManager()

@click.command()
@click.argument("query", required=False)
@click.option("--detailed", is_flag=True, help="Show detailed server information")
def search(query, detailed=False):
    """Search available MCP servers.
    
    Searches the MCP registry for available servers. Without arguments, lists all available servers.
    
    Examples:
        mcpm search                  # List all available servers
        mcpm search github           # Search for github server
        mcpm search --detailed       # Show detailed information
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
        if detailed:
            _display_detailed_results(servers)
        else:
            _display_table_results(servers)
        
        # Show summary count
        console.print(f"\n[green]Found {len(servers)} server(s) matching search criteria[/]")
        
    except Exception as e:
        console.print(f"[bold red]Error searching for servers:[/] {str(e)}")

def _display_table_results(servers):
    """Display search results in a compact table"""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Version")
    table.add_column("Description")
    table.add_column("Categories/Tags", overflow="fold")
    
    for server in sorted(servers, key=lambda s: s["name"]):
        # Get server data
        name = server["name"]
        display_name = server.get("display_name", name)
        version = server.get("version", "")
        description = server.get("description", "No description")
        
        # Build categories and tags
        categories = server.get("categories", [])
        tags = server.get("tags", [])
        meta_info = ", ".join([f"[dim]{c}[/]" for c in categories] + 
                         [f"[dim]{t}[/]" for t in tags])
        
        # Add row to table
        table.add_row(
            f"{display_name}\n[dim]({name})[/]",
            version,
            description,
            meta_info
        )
    
    console.print(table)

def _display_detailed_results(servers):
    """Display detailed information about each server"""
    for server in sorted(servers, key=lambda s: s["name"]):
        # Get server data
        name = server["name"]
        display_name = server.get("display_name", name)
        version = server.get("version", "")
        description = server.get("description", "No description")
        license_info = server.get("license", "Unknown")
        
        # Get author info
        author_info = server.get("author", {})
        author_name = author_info.get("name", "Unknown")
        author_email = author_info.get("email", "")
        
        # Installation requirements
        requirements = server.get("requirements", {})
        needs_api_key = requirements.get("api_key", False)
        auth_type = requirements.get("authentication")
        
        # Build categories and tags
        categories = server.get("categories", [])
        tags = server.get("tags", [])
        
        # Installation info
        installation = server.get("installation", {})
        package = installation.get("package", "")
        
        # Build the panel content
        content = f"[bold]{display_name}[/] [dim]v{version}[/]\n"
        content += f"[italic]{description}[/]\n\n"
        
        # Server information section
        content += "[bold yellow]Server Information:[/]\n"
        content += f"ID: {name}\n"
        if categories:
            content += f"Categories: {', '.join(categories)}\n"
        if tags:
            content += f"Tags: {', '.join(tags)}\n"
        content += f"Package: {package}\n" if package else ""
        content += f"Author: {author_name}" + (f" ({author_email})" if author_email else "") + "\n"
        content += f"License: {license_info}\n"
        
        # Requirements section if needed
        if needs_api_key:
            content += "\n[bold yellow]Authentication:[/]\n"
            content += "Requires API key or authentication\n"
            if auth_type:
                content += f"Authentication type: {auth_type}\n"
        
        # No installation status in the new architecture
        content += "\n"
        
        # If there are examples, show the first one
        examples = server.get("examples", [])
        if examples:
            content += "\n[bold yellow]Example:[/]\n"
            first_example = examples[0]
            if "title" in first_example:
                content += f"[bold]{first_example['title']}[/]\n"
            if "description" in first_example:
                content += f"{first_example['description']}\n"
        
        # Use a consistent border style in the new architecture
        border_style = "blue"
        panel = Panel(
            content,
            title=f"MCP Server: {name}",
            border_style=border_style,
            expand=False,
        )
        console.print(panel)
        console.print("")

