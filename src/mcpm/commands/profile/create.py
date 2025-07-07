"""Profile create command."""

from rich.console import Console

from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.rich_click_config import click

console = Console()
profile_config_manager = ProfileConfigManager()


@click.command(name="create")
@click.argument("profile")
@click.option("--force", is_flag=True, help="Force add even if profile already exists")
@click.help_option("-h", "--help")
def create_profile(profile, force=False):
    """Create a new MCPM profile."""
    if profile_config_manager.get_profile(profile) is not None and not force:
        console.print(f"[bold red]Error:[/] Profile '{profile}' already exists.")
        console.print("Use '--force' to overwrite the existing profile.")
        return

    profile_config_manager.new_profile(profile)

    console.print(f"\\n[green]Profile '{profile}' created successfully.[/]\\n")
    console.print(f"You can now edit this profile to add servers using 'mcpm profile edit {profile}'\\n")
