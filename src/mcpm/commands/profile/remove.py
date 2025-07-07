"""Profile remove command."""

from rich.console import Console
from rich.prompt import Confirm

from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.rich_click_config import click

console = Console()
profile_config_manager = ProfileConfigManager()


@click.command(name="rm")
@click.argument("profile_name")
@click.option("--force", "-f", is_flag=True, help="Force removal without confirmation")
@click.help_option("-h", "--help")
def remove_profile(profile_name, force):
    """Remove a profile.

    Deletes the specified profile and all its server associations.
    The servers themselves remain in the global configuration.

    Examples:

    \\b
        mcpm profile rm old-profile         # Remove with confirmation
        mcpm profile rm old-profile --force # Remove without confirmation
    """
    # Check if profile exists
    if profile_config_manager.get_profile(profile_name) is None:
        console.print(f"[red]Error: Profile '[bold]{profile_name}[/]' not found[/]")
        console.print()
        console.print("[yellow]Available options:[/]")
        console.print("  • Run 'mcpm profile ls' to see available profiles")
        return 1

    # Get profile info for confirmation
    profile_servers = profile_config_manager.get_profile(profile_name)
    server_count = len(profile_servers) if profile_servers else 0

    # Confirmation (unless forced)
    if not force:
        console.print(f"[yellow]About to remove profile '[bold]{profile_name}[/]'[/]")
        if server_count > 0:
            console.print(f"[dim]This profile contains {server_count} server(s)[/]")
            console.print("[dim]The servers will remain in global configuration[/]")
        console.print()

        confirm_removal = Confirm.ask("Are you sure you want to remove this profile?", default=False)

        if not confirm_removal:
            console.print("[yellow]Profile removal cancelled[/]")
            return 0

    # Remove the profile
    success = profile_config_manager.delete_profile(profile_name)

    if success:
        console.print(f"[green]✅ Profile '[cyan]{profile_name}[/]' removed successfully[/]")
        if server_count > 0:
            console.print(f"[dim]{server_count} server(s) remain available in global configuration[/]")
    else:
        console.print(f"[red]Error removing profile '[bold]{profile_name}[/]'[/]")
        return 1

    return 0
