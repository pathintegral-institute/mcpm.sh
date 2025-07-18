"""
New command - alias for 'edit -N' to create new server configurations
"""

from mcpm.commands.edit import _create_new_server
from mcpm.utils.rich_click_config import click


@click.command(name="new", context_settings=dict(help_option_names=["-h", "--help"]))
def new():
    """Create a new server configuration.

    This is an alias for 'mcpm edit -N' that opens an interactive form to create
    a new MCP server configuration. You can create either STDIO servers (local
    commands) or remote servers (HTTP/SSE).

    Examples:

        mcpm new                                      # Create new server interactively
        mcpm edit -N                                  # Equivalent command
    """
    return _create_new_server()
