"""Stash command for MCPM - temporarily stores server configuration aside"""

import logging

import click
from rich.console import Console

from mcpm.clients.client_config import ClientConfigManager
from mcpm.commands.target_operations.common import (
    client_get_server,
    client_remove_server,
    determine_target,
    profile_get_server,
    profile_remove_server,
)
from mcpm.utils.scope import ScopeType, format_scope

console = Console()
logger = logging.getLogger(__name__)
client_config_manager = ClientConfigManager()


@click.command()
@click.argument("server_name")
@click.help_option("-h", "--help")
def stash(server_name):
    """Temporarily store a server configuration aside.

    This command disables an active server without removing it, storing its
    configuration for later use. You can restore it with the 'pop' command.

    Examples:

    \b
        mcpm stash memory
        mcpm stash @cursor/memory
        mcpm stash %profile/memory
    """
    scope_type, scope, server_name = determine_target(server_name)
    if not scope_type or not scope or not server_name:
        return

    if scope_type == ScopeType.CLIENT:
        server_config = client_get_server(scope, server_name)
        if not server_config:
            console.print(f"[bold red]Error:[/] Server '{server_name}' not found in {scope}.")
            return
    else:
        server_config = profile_get_server(scope, server_name)
        if not server_config:
            console.print(f"[bold red]Error:[/] Server '{server_name}' not found in {scope}.")
            return

    # Convert ServerConfig to dictionary for storage
    server_data = server_config.to_dict()

    scope_name = format_scope(scope_type, scope)
    # Check if server is already stashed
    if client_config_manager.is_server_stashed(scope_name, server_name):
        console.print(f"[bold red]Error:[/] Server '{server_name}' is already stashed for {scope}.")
        return

    # Display server information before stashing
    console.print(f"\n[bold cyan]Stashing server:[/] {server_name}")

    # Store server in global config's stashed_servers
    stash_success = client_config_manager.stash_server(scope_name, server_name, server_data)

    # Remove the server from the client's configuration
    if stash_success:
        if scope_type == ScopeType.CLIENT:
            remove_success = client_remove_server(scope, server_name)
        else:
            remove_success = profile_remove_server(scope, server_name)

        if remove_success:
            console.print(f"[bold yellow]Stashed[/] MCP server '{server_name}' for {scope}")
            console.print("Server configuration is stored and can be restored with 'mcpm pop'.")
        else:
            # If removing failed, also remove from stashed servers to avoid issues
            client_config_manager.pop_server(scope_name, server_name)
            console.print(f"[bold red]Failed to remove server from {scope}. Stashing aborted.")
    else:
        console.print(f"[bold red]Failed to stash[/] '{server_name}' for {scope}.")
