"""Profile edit command."""

import sys

from rich.console import Console

from mcpm.global_config import GlobalConfigManager
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.non_interactive import is_non_interactive, parse_server_list, should_force_operation
from mcpm.utils.rich_click_config import click

from .interactive import interactive_profile_edit

console = Console()
profile_config_manager = ProfileConfigManager()
global_config_manager = GlobalConfigManager()


@click.command(name="edit")
@click.argument("profile_name")
@click.option("--name", type=str, help="New profile name")
@click.option("--servers", type=str, help="Comma-separated list of server names to include (replaces all)")
@click.option("--add-server", type=str, help="Comma-separated list of server names to add")
@click.option("--remove-server", type=str, help="Comma-separated list of server names to remove")
@click.option("--set-servers", type=str, help="Comma-separated list of server names to set (alias for --servers)")
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
@click.help_option("-h", "--help")
def edit_profile(profile_name, name, servers, add_server, remove_server, set_servers, force):
    """Edit a profile's name and server selection.

    Interactive by default, or use CLI parameters for automation.
    Use --add-server/--remove-server for incremental changes.
    """
    # Check if profile exists
    existing_servers = profile_config_manager.get_profile(profile_name)
    if existing_servers is None:
        console.print(f"[red]Error: Profile '[bold]{profile_name}[/]' not found[/]")
        console.print()
        console.print("[yellow]Available options:[/]")
        console.print("  • Run 'mcpm profile ls' to see available profiles")
        console.print("  • Run 'mcpm profile create {name}' to create a profile")
        sys.exit(1)

    # Detect if this is non-interactive mode
    has_cli_params = any([name, servers, add_server, remove_server, set_servers])
    force_non_interactive = is_non_interactive() or should_force_operation() or force

    if has_cli_params or force_non_interactive:
        exit_code = _edit_profile_non_interactive(
            profile_name=profile_name,
            new_name=name,
            servers=servers,
            add_server=add_server,
            remove_server=remove_server,
            set_servers=set_servers,
            force=force,
        )
        sys.exit(exit_code)

    else:
        # Interactive mode using InquirerPy
        console.print(f"[bold green]Opening Interactive Profile Editor: [cyan]{profile_name}[/]")
        console.print("[dim]Use arrow keys to navigate, space to select/deselect, type to search, enter to confirm[/]")
        console.print()

        # Get all available servers from global configuration
        all_servers = global_config_manager.list_servers()

        if not all_servers:
            console.print("[yellow]No servers found in global configuration[/]")
            console.print("[dim]Install servers first with 'mcpm install <server-name>'[/]")
            return 1

        # Get currently selected servers
        current_server_names = {server.name for server in existing_servers} if existing_servers else set()

        # Run the interactive form
        try:
            result = interactive_profile_edit(profile_name, all_servers, current_server_names)

            if result is None:
                console.print("[yellow]Interactive editing not available, falling back to non-interactive mode[/]")
                console.print("[dim]Use --name and --servers options to edit the profile[/]")
                return 1

            if result.get("cancelled", True):
                console.print("[yellow]Profile editing cancelled[/]")
                return 0

            # Extract results from InquirerPy form
            new_name = result["name"]
            selected_servers = result["servers"]

            # Check if new name conflicts with existing profiles (if changed)
            if new_name != profile_name and profile_config_manager.get_profile(new_name) is not None:
                console.print(f"[red]Error: Profile '[bold]{new_name}[/]' already exists[/]")
                return 1

        except Exception as e:
            console.print(f"[red]Error running interactive editor: {e}[/]")
            return 1

    console.print()

    # Show summary
    console.print("[bold]Summary of changes:[/]")
    console.print(f"Profile name: [cyan]{profile_name}[/] → [cyan]{new_name}[/]")
    console.print(f"Selected servers: [cyan]{len(selected_servers)} servers[/]")

    if selected_servers:
        for server_name in sorted(selected_servers):
            console.print(f"  • {server_name}")
    else:
        console.print("  [dim]No servers selected[/]")

    console.print()

    # Confirmation (only for non-interactive mode, InquirerPy handles its own confirmation)
    if is_non_interactive:
        console.print("[bold green]Applying changes...[/]")

    # Apply changes
    try:
        # If name changed, create new profile and delete old one
        if new_name != profile_name:
            # Create new profile with selected servers
            profile_config_manager.new_profile(new_name)

            # Add selected servers to new profile (using efficient tagging)
            for server_name in selected_servers:
                profile_config_manager.add_server_to_profile(new_name, server_name)

            # Delete old profile
            profile_config_manager.delete_profile(profile_name)

            console.print(f"[green]✅ Profile renamed from '[cyan]{profile_name}[/]' to '[cyan]{new_name}[/]'[/]")
        else:
            # Same name, just update servers
            # Clear current servers
            profile_config_manager.clear_profile(profile_name)

            # Add selected servers (using efficient tagging)
            for server_name in selected_servers:
                profile_config_manager.add_server_to_profile(profile_name, server_name)

            console.print(f"[green]✅ Profile '[cyan]{profile_name}[/]' updated[/]")

        console.print(f"[green]✅ {len(selected_servers)} servers configured in profile[/]")

    except Exception as e:
        console.print(f"[red]Error updating profile: {e}[/]")
        return 1

    return 0


def _edit_profile_non_interactive(
    profile_name: str,
    new_name: str = None,
    servers: str = None,
    add_server: str = None,
    remove_server: str = None,
    set_servers: str = None,
    force: bool = False,
) -> int:
    """Edit a profile non-interactively."""
    try:
        # Check if profile exists
        existing_servers = profile_config_manager.get_profile(profile_name)
        if existing_servers is None:
            console.print(f"[red]Error: Profile '[bold]{profile_name}[/]' not found[/]")
            return 1

        # Get all available servers for validation
        all_servers = global_config_manager.list_servers()
        if not all_servers:
            console.print("[yellow]No servers found in global configuration[/]")
            console.print("[dim]Install servers first with 'mcpm install <server-name>'[/]")
            return 1

        # Handle profile name
        final_name = new_name if new_name is not None else profile_name

        # Check if new name conflicts with existing profiles (if changed)
        if final_name != profile_name and profile_config_manager.get_profile(final_name) is not None:
            console.print(f"[red]Error: Profile '[bold]{final_name}[/]' already exists[/]")
            return 1

        # Start with current servers
        current_server_names = {server.name for server in existing_servers} if existing_servers else set()
        final_servers = current_server_names.copy()

        # Validate conflicting options
        server_options = [servers, add_server, remove_server, set_servers]
        if sum(1 for opt in server_options if opt is not None) > 1:
            console.print("[red]Error: Cannot use multiple server options simultaneously[/]")
            console.print("[dim]Use either --servers, --add-server, --remove-server, or --set-servers[/]")
            return 1

        # Handle server operations
        if servers is not None or set_servers is not None:
            # Set servers (replace all)
            server_list = servers if servers is not None else set_servers
            requested_servers = parse_server_list(server_list)

            # Validate servers exist
            invalid_servers = [s for s in requested_servers if s not in all_servers]
            if invalid_servers:
                console.print(f"[red]Error: Server(s) not found: {', '.join(invalid_servers)}[/]")
                console.print()
                console.print("[yellow]Available servers:[/]")
                for server_name in sorted(all_servers.keys()):
                    console.print(f"  • {server_name}")
                return 1

            final_servers = set(requested_servers)

        elif add_server is not None:
            # Add servers to existing
            servers_to_add = parse_server_list(add_server)

            # Validate servers exist
            invalid_servers = [s for s in servers_to_add if s not in all_servers]
            if invalid_servers:
                console.print(f"[red]Error: Server(s) not found: {', '.join(invalid_servers)}[/]")
                console.print()
                console.print("[yellow]Available servers:[/]")
                for server_name in sorted(all_servers.keys()):
                    console.print(f"  • {server_name}")
                return 1

            final_servers.update(servers_to_add)

        elif remove_server is not None:
            # Remove servers from existing
            servers_to_remove = parse_server_list(remove_server)

            # Validate servers are currently in profile
            not_in_profile = [s for s in servers_to_remove if s not in current_server_names]
            if not_in_profile:
                console.print(f"[yellow]Warning: Server(s) not in profile: {', '.join(not_in_profile)}[/]")

            final_servers.difference_update(servers_to_remove)

        # Display changes
        console.print(f"\n[bold green]Updating profile '{profile_name}':[/]")

        changes_made = False

        if final_name != profile_name:
            console.print(f"Name: [dim]{profile_name}[/] → [cyan]{final_name}[/]")
            changes_made = True

        if final_servers != current_server_names:
            console.print(f"Servers: [dim]{len(current_server_names)} servers[/] → [cyan]{len(final_servers)} servers[/]")

            # Show added servers
            added_servers = final_servers - current_server_names
            if added_servers:
                console.print(f"  [green]+ Added: {', '.join(sorted(added_servers))}[/]")

            # Show removed servers
            removed_servers = current_server_names - final_servers
            if removed_servers:
                console.print(f"  [red]- Removed: {', '.join(sorted(removed_servers))}[/]")

            changes_made = True

        if not changes_made:
            console.print("[yellow]No changes specified[/]")
            return 0

        # Apply changes
        console.print("\n[bold green]Applying changes...[/]")

        # If name changed, create new profile and delete old one
        if final_name != profile_name:
            # Create new profile with selected servers
            profile_config_manager.new_profile(final_name)

            # Add selected servers to new profile
            for server_name in final_servers:
                profile_config_manager.add_server_to_profile(final_name, server_name)

            # Delete old profile
            profile_config_manager.delete_profile(profile_name)

            console.print(f"[green]✅ Profile renamed from '[cyan]{profile_name}[/]' to '[cyan]{final_name}[/]'[/]")
        else:
            # Same name, just update servers
            # Clear current servers
            profile_config_manager.clear_profile(profile_name)

            # Add selected servers
            for server_name in final_servers:
                profile_config_manager.add_server_to_profile(profile_name, server_name)

            console.print(f"[green]✅ Profile '[cyan]{profile_name}[/]' updated[/]")

        console.print(f"[green]✅ {len(final_servers)} servers configured in profile[/]")

        return 0

    except Exception as e:
        console.print(f"[red]Error updating profile: {e}[/]")
        return 1
