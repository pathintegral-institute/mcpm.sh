"""Profile edit command."""

from rich.console import Console

from mcpm.global_config import GlobalConfigManager
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.rich_click_config import click

from .interactive import interactive_profile_edit

console = Console()
profile_config_manager = ProfileConfigManager()
global_config_manager = GlobalConfigManager()


@click.command(name="edit")
@click.argument("profile_name")
@click.option("--name", type=str, help="New profile name (non-interactive)")
@click.option("--servers", type=str, help="Comma-separated list of server names to include (non-interactive)")
@click.help_option("-h", "--help")
def edit_profile(profile_name, name, servers):
    """Edit a profile's name and server selection.

    By default, opens an advanced interactive form editor that allows you to:
    - Change the profile name with real-time validation
    - Select servers using a modern checkbox interface with search
    - Navigate with arrow keys, select with space, and search by typing

    For non-interactive usage, use --name and/or --servers options.

    Examples:

    \\b
        mcpm profile edit web-dev                           # Interactive form
        mcpm profile edit web-dev --name frontend-tools    # Rename only
        mcpm profile edit web-dev --servers time,sqlite    # Set servers only
        mcpm profile edit web-dev --name new-name --servers time,weather  # Both
    """
    # Check if profile exists
    existing_servers = profile_config_manager.get_profile(profile_name)
    if existing_servers is None:
        console.print(f"[red]Error: Profile '[bold]{profile_name}[/]' not found[/]")
        console.print()
        console.print("[yellow]Available options:[/]")
        console.print("  • Run 'mcpm profile ls' to see available profiles")
        console.print("  • Run 'mcpm profile create {name}' to create a profile")
        return 1

    # Detect if this is non-interactive mode
    is_non_interactive = name is not None or servers is not None

    if is_non_interactive:
        # Non-interactive mode
        console.print(f"[bold green]Editing Profile: [cyan]{profile_name}[/] [dim](non-interactive)[/]")
        console.print()

        # Handle profile name
        new_name = name if name is not None else profile_name

        # Check if new name conflicts with existing profiles (if changed)
        if new_name != profile_name and profile_config_manager.get_profile(new_name) is not None:
            console.print(f"[red]Error: Profile '[bold]{new_name}[/]' already exists[/]")
            return 1

        # Handle server selection
        if servers is not None:
            # Parse comma-separated server list
            requested_servers = [s.strip() for s in servers.split(",") if s.strip()]

            # Get all available servers for validation
            all_servers = global_config_manager.list_servers()
            if not all_servers:
                console.print("[yellow]No servers found in global configuration[/]")
                console.print("[dim]Install servers first with 'mcpm install <server-name>'[/]")
                return 1

            # Validate requested servers exist
            invalid_servers = [s for s in requested_servers if s not in all_servers]
            if invalid_servers:
                console.print(f"[red]Error: Server(s) not found: {', '.join(invalid_servers)}[/]")
                console.print()
                console.print("[yellow]Available servers:[/]")
                for server_name in sorted(all_servers.keys()):
                    console.print(f"  • {server_name}")
                return 1

            selected_servers = set(requested_servers)
        else:
            # Keep current server selection
            selected_servers = {server.name for server in existing_servers} if existing_servers else set()
            # Get all servers for applying changes
            all_servers = global_config_manager.list_servers()

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
