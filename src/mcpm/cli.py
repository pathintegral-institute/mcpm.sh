"""
MCPM CLI - Main entry point for the Model Context Protocol Manager CLI
"""

import click
from rich.console import Console
from rich.table import Table

from mcpm import __version__
from mcpm.clients.client_config import ClientConfigManager
from mcpm.commands import (
    add,
    client,
    config,
    doctor,
    import_client,
    info,
    inspect,
    inspector,
    list,
    profile,
    remove,
    router,
    run,
    search,
    usage,
)
from mcpm.commands.share import share

console = Console()
client_config_manager = ClientConfigManager()

# Set -h as an alias for --help but we'll handle it ourselves
CONTEXT_SETTINGS = dict(help_option_names=[])


def create_deprecated_command(command_name: str, replacement_suggestions=None):
    """Create a deprecated command that shows v2.0 migration guidance."""
    if replacement_suggestions is None:
        replacement_suggestions = [
            "mcpm install <server>                    # Install servers globally",
            "mcpm profile add <profile> <server>      # Tag servers with profiles", 
            "mcpm run <server>                        # Run servers directly"
        ]
    
    @click.command(context_settings=dict(ignore_unknown_options=True, help_option_names=[]))
    @click.option('--help', '-h', 'help_requested', is_flag=True, help='Show deprecation message.')
    @click.argument('args', nargs=-1, type=click.UNPROCESSED)
    def deprecated_command(help_requested, args):
        f"""The '{command_name}' command has been removed in MCPM v2.0."""
        console.print(f"[bold red]Error:[/] The 'mcpm {command_name}' command has been removed in MCPM v2.0.")
        console.print("[yellow]Use the new global configuration model instead:[/]")
        console.print()
        console.print("[cyan]New approach:[/]")
        for suggestion in replacement_suggestions:
            console.print(f"  [dim]{suggestion}[/]")
        console.print()
        raise click.ClickException("Command has been removed in v2.0")
    
    # Set the name properly on the command
    deprecated_command.name = command_name
    return deprecated_command


def print_logo():
    # Create bold ASCII art with thicker characters for a more striking appearance
    logo = [
        " ███╗   ███╗ ██████╗██████╗ ███╗   ███╗ ",
        " ████╗ ████║██╔════╝██╔══██╗████╗ ████║ ",
        " ██╔████╔██║██║     ██████╔╝██╔████╔██║ ",
        " ██║╚██╔╝██║██║     ██╔═══╝ ██║╚██╔╝██║ ",
        " ██║ ╚═╝ ██║╚██████╗██║     ██║ ╚═╝ ██║ ",
        " ╚═╝     ╚═╝ ╚═════╝╚═╝     ╚═╝     ╚═╝ ",
        "",
        f"v{__version__}",
        "Open Source. Forever Free.",
        "Built with ❤️ by Path Integral Institute",
    ]

    # Define terminal width for centering
    terminal_width = 80  # Standard terminal width

    # Print separator line
    console.print("[bold cyan]" + "=" * terminal_width + "[/]")

    # Calculate base padding for ASCII art
    base_padding = " " * ((terminal_width - len(logo[0])) // 2)

    # Center the ASCII art (except last line)
    for i in range(5):  # First 5 lines of the ASCII art
        console.print(f"{base_padding}[bold green]{logo[i]}[/]")

    # Print last line with version, using the same base padding
    version_text = f"v{__version__}"
    console.print(f"{base_padding}[bold green]{logo[5]}[/] [bold yellow]{version_text}[/]")

    # Center the taglines
    tagline1 = logo[8]  # "Open Source. Forever Free."
    tagline2 = logo[9]  # "Built with ❤️ by Path Integral Institute"

    # Calculate center padding for each tagline
    tagline1_padding = " " * ((terminal_width - len(tagline1)) // 2)
    tagline2_padding = " " * ((terminal_width - len(tagline2)) // 2)

    # Print centered taglines
    console.print(tagline1_padding + "[bold magenta]" + tagline1 + "[/]")
    console.print(tagline2_padding + "[bold cyan]" + tagline2 + "[/]")

    # Print separator line
    console.print("[bold cyan]" + "=" * terminal_width + "[/]")


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option("-h", "--help", "help_flag", is_flag=True, help="Show this message and exit.")
@click.option("-v", "--version", is_flag=True, help="Show version and exit.")
@click.pass_context
def main(ctx, help_flag, version):
    """MCPM - Model Context Protocol Manager.

    A simplified tool for managing MCP servers in a global configuration.
    Install servers, organize them with profiles, and run them directly.
    """
    if version:
        print_logo()
        return

    # v2.0 simplified model - no active target system
    # If no command was invoked or help is requested, show our custom help
    if ctx.invoked_subcommand is None or help_flag:
        print_logo()
        
        # Display usage info for new simplified model
        console.print("[bold green]Usage:[/] [white]mcpm [OPTIONS] COMMAND [ARGS]...[/]")
        console.print("")
        console.print("[bold green]Description:[/] [white]Manage MCP servers in a global configuration with profile organization.[/]")
        console.print("")
        
        # Show quick start examples
        console.print("[bold cyan]Quick Start:[/]")
        console.print("  [dim]mcpm search browser          # Find available servers[/]")
        console.print("  [dim]mcpm install mcp-server-browse  # Install a server[/]") 
        console.print("  [dim]mcpm run mcp-server-browse      # Run server directly[/]")
        console.print("  [dim]mcpm profile create web-dev     # Create a profile[/]")
        console.print("  [dim]mcpm profile add web-dev mcp-server-browse  # Tag server[/]")
        console.print("")

        # Display options
        console.print("[bold]Options:[/]")
        console.print("  --version   Show the version and exit.")
        console.print("  -h, --help  Show this message and exit.")
        console.print("")

        # Display available commands in a table
        console.print("[bold]Commands:[/]")
        commands_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))

        commands_table.add_row("[yellow]Server Management[/]")
        commands_table.add_row("  [cyan]search[/]", "Search available MCP servers from registry.")
        commands_table.add_row("  [cyan]info[/]", "Show detailed registry information for a server.")
        commands_table.add_row("  [cyan]install[/]", "Install a server from registry, local file, or URL.")
        commands_table.add_row("  [cyan]uninstall[/]", "Remove a server from configuration.")
        commands_table.add_row("  [cyan]ls[/]", "List all installed servers and profile assignments.")
        commands_table.add_row("  [cyan]inspect[/]", "Launch MCP Inspector to test/debug a server.")
        commands_table.add_row("  [cyan]import[/]", "Import server configurations from supported clients.")

        commands_table.add_row("[yellow]Server Execution[/]")
        commands_table.add_row("  [cyan]run[/]", "Execute a single server over stdio.")

        commands_table.add_row("[yellow]Profile Management[/]")
        commands_table.add_row("  [cyan]profile[/]", "Manage server profiles and tags.")

        commands_table.add_row("[yellow]Server Sharing[/]")
        commands_table.add_row("  [cyan]share[/]", "Share a single server through secure tunnel.")

        commands_table.add_row("[yellow]System & Configuration[/]")
        commands_table.add_row("  [cyan]doctor[/]", "Check system health and server status.")
        commands_table.add_row("  [cyan]usage[/]", "Display analytics and usage data.")
        commands_table.add_row("  [cyan]config[/]", "Manage MCPM configuration and settings.")

        commands_table.add_row("[yellow]Legacy Commands[/]")
        commands_table.add_row("  [cyan]add[/]", "Legacy: use 'install' instead.")
        commands_table.add_row("  [cyan]rm[/]", "Legacy: use 'uninstall' instead.")
        commands_table.add_row("  [cyan]client[/]", "Legacy: client management (use global config).")
        commands_table.add_row("  [cyan]stash/pop/mv/cp/target[/]", "Legacy: removed in v2.0 (use profiles).")
        console.print(commands_table)

        # Additional helpful information
        console.print("")
        console.print("[italic]Run [bold]mcpm COMMAND -h[/] for more information on a command.[/]")


# Register v2.0 commands
main.add_command(search.search)
main.add_command(info.info)
main.add_command(list.list, name="ls")
main.add_command(add.add, name="install")
main.add_command(remove.remove, name="uninstall")
main.add_command(run.run)
main.add_command(inspect.inspect)
main.add_command(profile.profile, name="profile")
main.add_command(import_client.import_client, name="import")
main.add_command(doctor.doctor)
main.add_command(usage.usage)
main.add_command(config.config)
main.add_command(share)

# Legacy command aliases that still work
main.add_command(add.add, name="add")  # Legacy alias for install
main.add_command(remove.remove, name="rm")  # Legacy alias for uninstall

# Deprecated v1 commands - show migration guidance
main.add_command(create_deprecated_command("stash"), name="stash")
main.add_command(create_deprecated_command("pop"), name="pop")
main.add_command(create_deprecated_command("mv", [
    "mcpm profile add <profile> <server>      # Tag servers with profiles",
    "mcpm profile remove <profile> <server>   # Remove tags from servers"
]), name="mv")
main.add_command(create_deprecated_command("cp", [
    "mcpm profile add <profile> <server>      # Tag servers with profiles", 
    "mcpm profile remove <profile> <server>   # Remove tags from servers"
]), name="cp")
main.add_command(create_deprecated_command("target"), name="target")

# Keep these for now but they could be simplified later
main.add_command(client.client)
main.add_command(inspector.inspector, name="inspector") 
main.add_command(router.router, name="router")

if __name__ == "__main__":
    main()
