"""
Search command for MCP - Search and display available MCP servers from the registry
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from mcp.utils.repository import RepositoryManager
from mcp.utils.config import ConfigManager

console = Console()
repo_manager = RepositoryManager()
config_manager = ConfigManager()

@click.command()
@click.argument("query", required=False)
@click.option("--tags", help="Filter servers by tag")
@click.option("--category", help="Filter servers by category")
@click.option("--detailed", is_flag=True, help="Show detailed server information")
@click.option("--installed", is_flag=True, help="Only show installed servers")
@click.option("--requires-auth", is_flag=True, help="Only show servers requiring authentication")
def search(query, tags=None, category=None, detailed=False, installed=False, requires_auth=False):
    """Search available MCP servers.
    
    Searches the MCP registry for available servers. Without arguments, lists all available servers.
    
    Examples:
        mcp search                  # List all available servers
        mcp search github           # Search for github server
        mcp search --tags=time      # Find servers with 'time' tag
        mcp search --category=api   # Find servers in 'api' category
        mcp search --detailed       # Show detailed information
        mcp search --installed      # Show only installed servers
    """
    # Show appropriate search message
    search_criteria = []
    if query:
        search_criteria.append(f"matching '[bold]{query}[/]'")
    if tags:
        search_criteria.append(f"with tag '[bold]{tags}[/]'")
    if category:
        search_criteria.append(f"in category '[bold]{category}[/]'")
    if installed:
        search_criteria.append("that are installed")
    if requires_auth:
        search_criteria.append("requiring authentication")
        
    if search_criteria:
        console.print(f"[bold green]Searching for MCP servers[/] {' '.join(search_criteria)}")
    else:
        console.print("[bold green]Listing all available MCP servers[/]")
    
    # Search for servers
    try:
        # Get list of installed servers for comparison
        installed_servers = config_manager.get_all_servers() or {}
        
        # Get all matching servers from registry
        servers = repo_manager.search_servers(query, tags, category)
        
        # Apply additional filters
        if installed:
            servers = [s for s in servers if s["name"] in installed_servers]
        
        if requires_auth:
            servers = [s for s in servers if s.get("requirements", {}).get("api_key", False)]
        
        if not servers:
            console.print("[yellow]No matching MCP servers found.[/]")
            return
        
        # Show different views based on detail level
        if detailed:
            _display_detailed_results(servers, installed_servers)
        else:
            _display_table_results(servers, installed_servers)
        
        # Show summary count
        console.print(f"\n[green]Found {len(servers)} server(s) matching search criteria[/]")
        
    except Exception as e:
        console.print(f"[bold red]Error searching for servers:[/] {str(e)}")

def _display_table_results(servers, installed_servers):
    """Display search results in a compact table"""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Version")
    table.add_column("Description")
    table.add_column("Categories/Tags", overflow="fold")
    table.add_column("Status")
    
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
        
        # Check installation status
        is_installed = name in installed_servers
        if is_installed:
            # Get installed version
            installed_version = installed_servers[name].get("version", "?")
            if installed_version == version:
                status = "[green]✓ Installed[/]"
            else:
                status = f"[yellow]↑ Update available[/]\n[dim]v{installed_version} → v{version}[/]"
        else:
            status = "[dim]Not installed[/]"
            
        # Check if requires auth
        if server.get("requirements", {}).get("api_key", False):
            status += "\n[dim]Requires auth[/]"
        
        # Add row to table
        table.add_row(
            f"{display_name}\n[dim]({name})[/]",
            version,
            description,
            meta_info,
            status
        )
    
    console.print(table)

def _display_detailed_results(servers, installed_servers):
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
        
        # Check installation status
        is_installed = name in installed_servers
        if is_installed:
            installed_version = installed_servers[name].get("version", "?")
            install_date = installed_servers[name].get("install_date", "Unknown")
            installation_status = f"✓ Installed (v{installed_version}, {install_date})"
            if installed_version != version:
                installation_status += f" - Update available to v{version}"
        else:
            installation_status = "Not installed"
        
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
        
        # Installation status
        content += f"\n[bold yellow]Status:[/] [bold]{installation_status}[/]\n"
        
        # If there are examples, show the first one
        examples = server.get("examples", [])
        if examples:
            content += "\n[bold yellow]Example:[/]\n"
            first_example = examples[0]
            if "title" in first_example:
                content += f"[bold]{first_example['title']}[/]\n"
            if "description" in first_example:
                content += f"{first_example['description']}\n"
        
        # Create panel with border color based on installation status
        border_style = "green" if is_installed else "blue"
        panel = Panel(
            content,
            title=f"MCP Server: {name}",
            border_style=border_style,
            expand=False,
        )
        console.print(panel)
        console.print("")

