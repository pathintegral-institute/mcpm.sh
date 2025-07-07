"""Profile management commands."""

from mcpm.utils.rich_click_config import click

from .create import create_profile
from .edit import edit_profile
from .inspect import inspect_profile
from .list import list_profiles
from .remove import remove_profile
from .run import run
from .share import share_profile


@click.group()
@click.help_option("-h", "--help")
def profile():
    """Manage MCPM profiles - collections of servers for different workflows.

    Profiles are named groups of MCP servers that work together for specific tasks or
    projects. They allow you to organize servers by purpose (e.g., 'web-dev', 'data-analysis')
    and run multiple related servers simultaneously through FastMCP proxy aggregation.

    Examples: 'frontend' profile with browser + github servers, 'research' with filesystem + web tools."""
    pass


# Register all profile subcommands
profile.add_command(list_profiles)
profile.add_command(create_profile)
profile.add_command(edit_profile)
profile.add_command(inspect_profile)
profile.add_command(share_profile)
profile.add_command(remove_profile)
profile.add_command(run)
