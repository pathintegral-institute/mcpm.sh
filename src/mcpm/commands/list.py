"""
List command for MCP v2.0 - Global Configuration Model
"""

import click
from rich.console import Console
from rich.table import Table

from mcpm.commands.target_operations.common import global_list_servers
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.display import print_server_config

console = Console()
profile_manager = ProfileConfigManager()


@click.command()
@click.option("--target", "-t", help="[DEPRECATED] Ignored in v2.0", hidden=True)
@click.help_option("-h", "--help")
def list(target: str | None = None):
    """List all installed MCP servers from global configuration.

    Examples:

    \b
        mcpm ls                    # List all servers in global config
        mcpm profile ls            # List profiles and their tagged servers
    """
    
    # v2.0: Use global configuration model
    console.print("[bold green]MCPM Global Configuration:[/]")
    
    # Get all servers from global configuration
    servers = global_list_servers()
    
    if not servers:
        console.print("\n[yellow]No MCP servers found in global configuration.[/]")
        console.print("Use 'mcpm install <server>' to install a server.")
        console.print()
        return

    # Get all profiles to show which servers are tagged
    profiles = profile_manager.list_profiles()
    
    # Create a mapping of server names to their profile tags
    server_profiles = {}
    for profile_name, profile_servers in profiles.items():
        for server in profile_servers:
            if server.name not in server_profiles:
                server_profiles[server.name] = []
            server_profiles[server.name].append(profile_name)

    console.print(f"\n[bold]Found {len(servers)} server(s) in global configuration:[/]")
    console.print()

    # Display servers with their profile tags
    for server_name, server_config in servers.items():
        # Show profile tags if any
        tags = server_profiles.get(server_name, [])
        if tags:
            tag_display = f" [dim](tagged: {', '.join(tags)})[/]"
        else:
            tag_display = " [dim](no profile tags)[/]"
        
        console.print(f"[bold cyan]{server_name}[/]{tag_display}")
        print_server_config(server_config)

    console.print()
