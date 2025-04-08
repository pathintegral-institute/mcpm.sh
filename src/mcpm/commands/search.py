"""
Search command for MCPM - Search and display available MCP servers from the registry
"""

import click
from rich.console import Console

from mcpm.utils.display import print_error, print_servers_table
from mcpm.utils.repository import RepositoryManager

console = Console()
repo_manager = RepositoryManager()


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
            print_servers_table(servers)

        # Show summary count
        console.print(f"\n[green]Found {len(servers)} server(s) matching search criteria[/]")

    except Exception as e:
        print_error("Error searching for servers", str(e))


def _display_detailed_results(servers):
    """Display detailed information about each server"""
    for i, server in enumerate(sorted(servers, key=lambda s: s["name"])):
        # Get server data
        name = server["name"]
        display_name = server.get("display_name", name)
        description = server.get("description", "No description")
        license_info = server.get("license", "Unknown")

        # Get author info
        author_info = server.get("author", {})
        author_name = author_info.get("name", "Unknown")
        author_email = author_info.get("email", "")

        # Build categories and tags
        categories = server.get("categories", [])
        tags = server.get("tags", [])

        # Get installation details
        installations = server.get("installations", {})
        installation = server.get("installation", {})
        package = installation.get("package", "")

        # Print server header
        console.print(f"[bold cyan]{display_name}[/] [dim]({name})[/]")
        console.print(f"[italic]{description}[/]\n")

        # Server information section
        console.print("[bold yellow]Server Information:[/]")
        if categories:
            console.print(f"Categories: {', '.join(categories)}")
        if tags:
            console.print(f"Tags: {', '.join(tags)}")
        if package:
            console.print(f"Package: {package}")
        console.print(f"Author: {author_name}" + (f" ({author_email})" if author_email else ""))
        console.print(f"License: {license_info}")
        console.print("")

        # Installation details section
        if installations:
            console.print("[bold yellow]Installation Details:[/]")
            for method in installations.values():
                method_type = method.get("type", "unknown")
                description = method.get("description", f"{method_type} installation")
                recommended = " [green](recommended)[/]" if method.get("recommended", False) else ""

                console.print(f"[cyan]{method_type}[/]: {description}{recommended}")

                # Show command if available
                if "command" in method:
                    cmd = method["command"]
                    args = method.get("args", [])
                    cmd_str = f"{cmd} {' '.join(args)}" if args else cmd
                    console.print(f"Command: [green]{cmd_str}[/]")

                # Show dependencies if available
                dependencies = method.get("dependencies", [])
                if dependencies:
                    console.print("Dependencies: " + ", ".join(dependencies))

                # Show environment variables if available
                env_vars = method.get("env", {})
                if env_vars:
                    console.print("Environment Variables:")
                    for key, value in env_vars.items():
                        console.print(f'  [bold blue]{key}[/] = [green]"{value}"[/]')
                console.print("")

        # If there are examples, show the first one
        examples = server.get("examples", [])
        if examples:
            console.print("[bold yellow]Example:[/]")
            first_example = examples[0]
            if "title" in first_example:
                console.print(f"[bold]{first_example['title']}[/]")
            if "description" in first_example:
                console.print(f"{first_example['description']}")
            console.print("")

        # Add a separator between servers (except for the last one)
        if i < len(servers) - 1:
            console.print("[dim]" + "-" * 50 + "[/]\n")
