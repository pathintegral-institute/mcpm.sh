"""Profile management commands."""

import click

from .create import create_profile
from .edit import edit_profile
from .list import list_profiles
from .remove import remove_profile
from .run import run
from .share import share_profile


@click.group()
@click.help_option("-h", "--help")
def profile():
    """Manage MCPM profiles."""
    pass


# Register all profile subcommands
profile.add_command(list_profiles)
profile.add_command(create_profile)
profile.add_command(edit_profile)
profile.add_command(share_profile)
profile.add_command(remove_profile)
profile.add_command(run)
