"""
List command for MCP v2.0 - Global Configuration Model
"""

from rich.console import Console

from mcpm.global_config import GlobalConfigManager
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.display import print_server_config
from mcpm.utils.rich_click_config import click

console = Console()
profile_manager = ProfileConfigManager()
global_config_manager = GlobalConfigManager()


def global_list_servers():
    """List all servers in the global MCPM configuration."""
    return global_config_manager.list_servers()


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed server configuration")
@click.help_option("-h", "--help")
def list(verbose: bool = False):
    """List all installed MCP servers from global configuration.

    Examples:

    \b
        mcpm ls                    # List server names and profiles
        mcpm ls -v                 # List servers with detailed configuration
        mcpm profile ls            # List profiles and their included servers
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

    # Display servers with their profiles
    for server_name, server_config in servers.items():
        # Show profiles if any
        profiles_list = server_profiles.get(server_name, [])
        if profiles_list:
            highlighted_profiles = [f"[yellow]{profile}[/]" for profile in profiles_list]
            profile_display = f" [dim](profiles:[/] {', '.join(highlighted_profiles)}[dim])[/]"
        else:
            profile_display = " [dim](no profiles)[/]"

        console.print(f"[bold cyan]{server_name}[/]{profile_display}")

        # Only show detailed config in verbose mode
        if verbose:
            print_server_config(server_config, show_name=False)

    console.print()

    # Add hint about verbose mode if not specified
    if not verbose:
        console.print("[dim]Tip: Use 'mcpm ls -v' to see detailed server configurations[/]")
        console.print()
