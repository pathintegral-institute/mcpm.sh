"""
List command for MCP
"""

import click
from pydantic import TypeAdapter
from rich.console import Console

from mcpm.clients.client_config import ClientConfigManager
from mcpm.clients.client_registry import ClientRegistry
from mcpm.commands.target_operations.common import determine_scope
from mcpm.core.schema import ServerConfig
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.display import print_client_error, print_server_config
from mcpm.utils.scope import ScopeType, format_scope

console = Console()
client_config_manager = ClientConfigManager()


@click.command()
@click.option("--target", "-t", help="Target to list servers from")
@click.help_option("-h", "--help")
def list(target: str | None = None):
    """List all installed MCP servers.

    Examples:

    \b
        mcpm ls
        mcpm ls -t @cursor
    """
    scope_type, scope = determine_scope(target)
    if not scope:
        return

    if scope_type == ScopeType.CLIENT:
        # Get the active client manager and information
        client_manager = ClientRegistry.get_client_manager(scope)
        if client_manager is None:
            print_client_error()
            return
        client_info = ClientRegistry.get_client_info(scope)
        client_name = client_info.get("name", scope)

        console.print(f"[bold green]MCP servers installed in {scope}:[/]")

        # Get all servers from active client config
        servers = client_manager.get_servers()

        # Get stashed servers
        formatted_scope = format_scope(scope_type, scope)
        stashed_servers = client_config_manager.get_stashed_servers(formatted_scope)

        if not servers and not stashed_servers:
            console.print(f"[yellow]No MCP servers found in {client_name}.[/]")
            console.print("Use 'mcpm add <server>' to add a server.")
            return

        # Print active servers
        if servers:
            console.print("\n[bold]Active Servers:[/]")
            for server_name, server_info in servers.items():
                print_server_config(client_manager.from_client_format(server_name, server_info))

        # Print stashed servers
        if stashed_servers:
            console.print("\n[bold]Stashed Servers:[/]")
            for server_name, server_info in stashed_servers.items():
                print_server_config(client_manager.from_client_format(server_name, server_info), is_stashed=True)
    else:
        # Get the active profile manager and information
        profile = scope
        profile_manager = ProfileConfigManager()
        servers = profile_manager.get_profile(profile)
        if servers is None:
            console.print(f"[bold red]Error:[/] Profile '{profile}' not found.")
            return
        # Get all servers from active profile config
        for server in servers:
            print_server_config(server)

        # Get stashed servers
        formatted_scope = format_scope(scope_type, scope)
        stashed_servers = client_config_manager.get_stashed_servers(formatted_scope)
        if stashed_servers:
            console.print("\n[bold]Stashed Servers:[/]")
            for server_name, server_info in stashed_servers.items():
                print_server_config(TypeAdapter(ServerConfig).validate_python(server_info), is_stashed=True)
    console.print("\n")
