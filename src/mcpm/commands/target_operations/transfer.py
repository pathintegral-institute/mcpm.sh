import click
from rich.console import Console

from mcpm.clients.client_registry import ClientRegistry
from mcpm.commands.target_operations.common import (
    client_add_server,
    client_get_server,
    client_remove_server,
    determine_target,
    profile_add_server,
    profile_get_server,
    profile_remove_server,
)
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.display import print_active_scope, print_no_active_scope
from mcpm.utils.scope import ScopeType, extract_from_scope

console = Console()
profile_manager = ProfileConfigManager()


def determine_source_and_destination(
    source: str, destination: str
) -> tuple[ScopeType | None, str | None, str | None, ScopeType | None, str | None, str | None]:
    source_context_type, source_context, source_server = determine_target(source)
    destination_context_type, destination_context, destination_server = determine_target(destination)
    if not source_context or not destination_context:
        active_context = ClientRegistry.get_active_target()
        if not active_context:
            print_no_active_scope()
            return None, None, None, None, None, None
        print_active_scope(active_context)
        active_context_type, active_context_name = extract_from_scope(active_context)
        if not source_context:
            source_context_type = active_context_type
            source_context = active_context_name
        if not destination_context:
            destination_context_type = active_context_type
            destination_context = active_context_name
    if not destination_server:
        destination_server = source_server
    return (
        source_context_type,
        source_context,
        source_server,
        destination_context_type,
        destination_context,
        destination_server,
    )


@click.command()
@click.argument("source")
@click.argument("destination")
@click.help_option("-h", "--help")
@click.option("--force", is_flag=True, help="Force copy even if destination already exists")
def copy(source, destination, force=False):
    """
    Copy a server configuration from one client/profile to another.

    Examples:

    \b
        mcpm cp memory memory2
        mcpm cp @cursor/memory @windsurf/memory
    """
    (
        source_context_type,
        source_context,
        source_server,
        destination_context_type,
        destination_context,
        destination_server,
    ) = determine_source_and_destination(source, destination)

    if not (
        source_context_type
        and destination_context_type
        and source_context
        and destination_context
        and source_server
        and destination_server
    ):
        return

    if source_context_type == ScopeType.CLIENT:
        source_server_config = client_get_server(source_context, source_server)
        if not source_server_config:
            console.print(f"[bold red]Error:[/] Server '{source_server}' not found in {source_context}.")
            return
    else:
        source_server_config = profile_get_server(source_context, source_server)
        if not source_server_config:
            console.print(f"[bold red]Error:[/] Server '{source_server}' not found in {source_context}.")
            return
    console.print(f"[bold green]Copying[/] server '{source_server}' from {source_context} to {destination_context}.")
    source_server_config.name = destination_server
    if destination_context_type == ScopeType.CLIENT:
        success = client_add_server(destination_context, source_server_config, force)
    else:
        success = profile_add_server(destination_context, source_server_config, force)
    if success:
        console.print(f"[green]Copied[/] {source_context} server '{source_server}' to {destination_context}.")
    else:
        console.print(
            f"[bold red]Error:[/] Failed to copy {source_context} server '{source_server}' to {destination_context}."
        )


@click.command()
@click.argument("source")
@click.argument("destination")
@click.option("--force", is_flag=True, help="Force move even if destination already exists")
@click.help_option("-h", "--help")
def move(source, destination, force=False):
    """
    Move a server configuration from one client/profile to another.

    Examples:

    \b
        mcpm mv memory memory2
        mcpm mv @cursor/memory @windsurf/memory
    """
    (
        source_context_type,
        source_context,
        source_server,
        destination_context_type,
        destination_context,
        destination_server,
    ) = determine_source_and_destination(source, destination)

    if not (
        source_context_type
        and destination_context_type
        and source_context
        and destination_context
        and source_server
        and destination_server
    ):
        return

    if source_context_type == ScopeType.CLIENT:
        source_server_config = client_get_server(source_context, source_server)
        if not source_server_config:
            console.print(f"[bold red]Error:[/] Server '{source_server}' not found in {source_context}.")
            return
    else:
        source_server_config = profile_get_server(source_context, source_server)
        if not source_server_config:
            console.print(f"[bold red]Error:[/] Server '{source_server}' not found in {source_context}.")
            return
    console.print(f"[bold green]Moving[/] server '{source_server}' from {source_context} to {destination_context}.")
    source_server_config.name = destination_server
    if destination_context_type == ScopeType.CLIENT:
        add_success = client_add_server(destination_context, source_server_config, force)
    else:
        add_success = profile_add_server(destination_context, source_server_config, force)
    if add_success:
        # try remove
        remove_success = False
        if source_context_type == ScopeType.CLIENT:
            remove_success = client_remove_server(source_context, source_server)
        else:
            remove_success = profile_remove_server(source_context, source_server)
        if remove_success:
            console.print(f"[green]Moved[/] {source_context} server '{source_server}' to {destination_context}.")
        else:
            console.print(
                f"[bold red]Error:[/] Failed to remove {source_context} server '{source_server}' from {source_context}"
            )
            # remove added
            if destination_context_type == ScopeType.CLIENT:
                client_remove_server(destination_context, destination_server)
            else:
                profile_remove_server(destination_context, destination_server)
    else:
        console.print(
            f"[bold red]Error:[/] Failed to move {source_context} server '{source_server}' to {destination_context}."
        )
