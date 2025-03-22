"""
MCPM CLI - Main entry point for the Model Context Protocol Package Manager CLI
"""

import sys
import click
from rich.console import Console
from rich.table import Table

from mcpm.utils.config import ConfigManager

from mcpm import __version__
from mcpm.commands import (
    search,
    install,
    remove,
    list_servers,
    config,
    status,
    enable,
    disable,
    server,
    client,
)

console = Console()
config_manager = ConfigManager()

# Set -h as an alias for --help
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.version_option(version=__version__)
@click.pass_context
def main(ctx):
    """MCPM - Model Context Protocol Package Manager.
    
    A tool for managing MCP servers across various clients.
    """
    # If no command was invoked, show the active client and complete command list
    if ctx.invoked_subcommand is None:
        # Check if help flag was used
        if '--help' in sys.argv or '-h' in sys.argv:
            # Let Click handle the help display
            return
        
        # Get active client
        active_client = config_manager.get_active_client()
        
        # Display active client information and main help
        console.print("[bold]MCPM - Model Context Protocol Package Manager[/]")
        console.print("")
        console.print(f"[bold cyan]Active client:[/] {active_client}")
        console.print("")
        
        # Display usage info
        console.print("[bold]Usage:[/] mcpm [OPTIONS] COMMAND [ARGS]...")
        console.print("")
        console.print("[bold]Description:[/] A tool for managing MCP servers across various clients.")
        console.print("")
        
        # Display options
        console.print("[bold]Options:[/]")
        console.print("  --version   Show the version and exit.")
        console.print("  -h, --help  Show this message and exit.")
        console.print("")
        
        # Display commands in a table
        console.print("[bold]Commands:[/]")
        commands_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        commands_table.add_row("  [cyan]client[/]", "Manage the active MCP client.")
        commands_table.add_row("  [cyan]config[/]", "View or edit the active MCP client's configuration file.")
        commands_table.add_row("  [cyan]disable[/]", "Disable an MCP server for a specific client.")
        commands_table.add_row("  [cyan]enable[/]", "Enable an MCP server for a specific client.")
        commands_table.add_row("  [cyan]install[/]", "Install an MCP server.")
        commands_table.add_row("  [cyan]list[/]", "List all installed MCP servers.")
        commands_table.add_row("  [cyan]remove[/]", "Remove an installed MCP server.")
        commands_table.add_row("  [cyan]search[/]", "Search available MCP servers.")
        commands_table.add_row("  [cyan]server[/]", "Manage MCP server processes.")
        commands_table.add_row("  [cyan]status[/]", "Show status of MCP servers in Claude Desktop.")
        console.print(commands_table)
        
        # Additional helpful information
        console.print("")
        console.print("[italic]Run [bold]mcpm CLIENT -h[/] for more information on a command.[/]")

# Register commands
main.add_command(search.search)
main.add_command(install.install)
main.add_command(remove.remove)
main.add_command(list_servers.list)
main.add_command(config.config)
main.add_command(status.status)
main.add_command(enable.enable)
main.add_command(disable.disable)
main.add_command(server.server)
main.add_command(client.client)

if __name__ == "__main__":
    main()
