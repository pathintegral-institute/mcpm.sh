"""
MCP CLI - Main entry point for the Model Context Protocol Package Manager CLI
"""

import click
from rich.console import Console
from rich.table import Table

from mcp.utils.config import ConfigManager

from mcp import __version__
from mcp.commands import (
    search,
    install,
    remove,
    list_servers,
    edit,
    status,
    toggle,
    server,
    client,
)

console = Console()
config_manager = ConfigManager()

# Set -h as an alias for --help but we'll handle it ourselves
CONTEXT_SETTINGS = dict(help_option_names=[])

@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option('-h', '--help', 'help_flag', is_flag=True, help='Show this message and exit.')
@click.version_option(version=__version__)
@click.pass_context
def main(ctx, help_flag):
    """MCP - Model Context Protocol Package Manager.
    
    A tool for managing MCP servers across various clients.
    """
    # If no command was invoked or help is requested, show our custom help
    if ctx.invoked_subcommand is None or help_flag:
        
        # Get active client
        active_client = config_manager.get_active_client()
        
        # Create a nice ASCII art banner with proper alignment using Rich
        from rich.panel import Panel
        
        # Create bold ASCII art with thicker characters for a more striking appearance
        logo = [
            " ███╗   ███╗ ██████╗██████╗                           ",
            " ████╗ ████║██╔════╝██╔══██╗                          ",
            " ██╔████╔██║██║     ██████╔╝                          ",
            " ██║╚██╔╝██║██║     ██╔═══╝                           ",
            " ██║ ╚═╝ ██║╚██████╗██║                               ",
            " ╚═╝     ╚═╝ ╚═════╝╚═╝                               ",
            "",
            f"v{__version__}",
            "Model Context Protocol Manager for all AI apps",
            "Supports Claude Desktop, Windsurf, and more"
        ]
        
        # No need to convert to joined string since we're formatting directly in the panel
        
        # Create a panel with styled content
        panel = Panel(
            f"[bold green]{logo[0]}\n{logo[1]}\n{logo[2]}\n{logo[3]}\n{logo[4]}\n{logo[5]}[/]\n\n[bold yellow]{logo[7]}[/]\n[italic blue]{logo[8]}[/]\n[bold magenta]{logo[9]}[/]",
            border_style="bold cyan",
            expand=False,
            padding=(0, 2),
        )
        
        # Print the panel
        console.print(panel)
        
        # Get information about installed clients
        from mcp.utils.client_detector import detect_installed_clients
        installed_clients = detect_installed_clients()
        
        # Display active client information and main help
        client_status = "[green]✓[/]" if installed_clients.get(active_client, False) else "[yellow]⚠[/]"
        console.print(f"[bold magenta]Active client:[/] [yellow]{active_client}[/] {client_status}")
        
        # Display all supported clients with their installation status
        console.print("[bold]Supported clients:[/]")
        for client, installed in installed_clients.items():
            status = "[green]Installed[/]" if installed else "[gray]Not installed[/]"
            active_marker = "[bold cyan]➤[/] " if client == active_client else "  "
            console.print(f"{active_marker}{client}: {status}")
        console.print("")
        
        # Display usage info
        console.print("[bold green]Usage:[/] [white]mcp [OPTIONS] COMMAND [ARGS]...[/]")
        console.print("")
        console.print("[bold green]Description:[/] [white]A tool for managing MCP servers across various clients.[/]")
        console.print("")
        
        # Display options
        console.print("[bold]Options:[/]")
        console.print("  --version   Show the version and exit.")
        console.print("  -h, --help  Show this message and exit.")
        console.print("")
        
        # Display available commands in a table
        console.print("[bold]Commands:[/]")
        commands_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        commands_table.add_row("  [cyan]client[/]", "Manage the active MCP client.")
        commands_table.add_row("  [cyan]edit[/]", "View or edit the active MCP client's configuration file.")
        commands_table.add_row("  [cyan]list[/]", "List all installed MCP servers.")
        commands_table.add_row("  [cyan]remove[/]", "Remove an installed MCP server.")
        commands_table.add_row("  [cyan]server[/]", "Manage MCP server processes.")
        commands_table.add_row("  [cyan]toggle[/]", "Toggle an MCP server on or off for a client.")
        console.print(commands_table)
        
        # Display coming soon commands
        console.print("")
        console.print("[bold yellow]Coming Soon:[/]")
        coming_soon_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        coming_soon_table.add_row("  [yellow]install[/]", "Install an MCP server.")
        coming_soon_table.add_row("  [yellow]search[/]", "Search available MCP servers.")
        coming_soon_table.add_row("  [yellow]status[/]", "Show status of MCP servers in Claude Desktop.")
        console.print(coming_soon_table)
        
        # Additional helpful information
        console.print("")
        console.print("[italic]Run [bold]mcp CLIENT -h[/] for more information on a command.[/]")

# Register commands
main.add_command(search.search)
main.add_command(install.install)
main.add_command(remove.remove)
main.add_command(list_servers.list)
main.add_command(edit.edit)
main.add_command(status.status)
main.add_command(toggle.toggle)
main.add_command(server.server)
main.add_command(client.client)

if __name__ == "__main__":
    main()
