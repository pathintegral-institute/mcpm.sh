"""Pop command for MCPM - restores previously stashed server configuration"""

import logging

import click
from pydantic import TypeAdapter
from rich.console import Console

from mcpm.clients.client_config import ClientConfigManager
from mcpm.clients.client_registry import ClientRegistry
from mcpm.commands.target_operations.common import determine_target
from mcpm.core.schema import ServerConfig
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.scope import ScopeType, format_scope

console = Console()
logger = logging.getLogger(__name__)
client_config_manager = ClientConfigManager()


@click.command()
@click.argument("server_name")
@click.help_option("-h", "--help")
def pop(server_name):
    """Restore a previously stashed server configuration.

    This command re-enables a previously stashed (disabled) server,
    restoring it to active status.

    Examples:

    \b
        mcpm pop memory
        mcpm pop %profile/memory
    """
    scope_type, scope, server_name = determine_target(server_name)
    if not scope_type or not scope or not server_name:
        return

    scope_name = format_scope(scope_type, scope)
    # Check if the server is stashed for this client
    if not client_config_manager.is_server_stashed(scope_name, server_name):
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in stashed configurations for {scope}.")
        return

    # Get the server configuration from global stashed servers
    server_data = client_config_manager.pop_server(scope_name, server_name)
    if not server_data:
        console.print(f"[bold red]Error:[/] Failed to retrieve stashed configuration for server '{server_name}'.")
        return

    # Convert the server configuration to the client's format and add it back
    # to the active servers
    if scope_type == ScopeType.CLIENT:
        client = scope
        # Get the active client manager and related information
        client_manager = ClientRegistry.get_client_manager(client)
        client_info = ClientRegistry.get_client_info(client)
        client_name = client_info.get("name", client)

        # Check if client is supported
        if client_manager is None:
            console.print("[bold red]Error:[/] Unsupported active client")
            console.print("Please switch to a supported client using 'mcpm target set @<client-name>'")
            return

        server_config = client_manager.from_client_format(server_name, server_data)
        success = client_manager.add_server(server_config)
    else:
        # Get the profile manager and related information
        profile_manager = ProfileConfigManager()
        server_config = TypeAdapter(ServerConfig).validate_python(server_data)
        success = profile_manager.set_profile(scope, server_config)

    if success:
        console.print(f"[bold green]Restored[/] MCP server '{server_name}' for {scope}")
        console.print("Remember to restart the client for changes to take effect.")
    else:
        # If adding failed, re-stash the server to avoid data loss
        client_config_manager.stash_server(scope_name, server_name, server_data)
        console.print(f"[bold red]Failed to restore[/] '{server_name}' for {client_name}.")
