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
    custom,
    info,
    inspector,
    list,
    pop,
    profile,
    remove,
    router,
    search,
    stash,
    target,
    transfer,
)
from mcpm.commands.share import share

console = Console()
client_config_manager = ClientConfigManager()

# Set -h as an alias for --help but we'll handle it ourselves
CONTEXT_SETTINGS = dict(help_option_names=[])


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

    A tool for managing MCP servers across various clients.
    """
    if version:
        print_logo()
        return

    # Check if a command is being executed (and it's not help, no command, or the client command)
    if (
        ctx.invoked_subcommand
        and ctx.invoked_subcommand not in ["target", "client", "profile", "router", "share", "inspector"]
        and not help_flag
    ):
        # Check if active client is set
        active_target = client_config_manager.get_active_target()
        if not active_target:
            console.print("[bold red]Error:[/] No active target set.")
            console.print("Please run 'mcpm target set <target>' to set an active target\n")

            # Show available clients
            from mcpm.clients.client_registry import ClientRegistry

            console.print("[bold green]Available Clients, set one with 'mcpm target set @<client>':[/]")
            for client in ClientRegistry.get_supported_clients():
                console.print(f"  - {client}")

            from mcpm.profile.profile_config import ProfileConfigManager

            # Show available profiles
            console.print("[bold green]Available Profiles, set one with 'mcpm target set %<profile>':[/]")
            profile_manager = ProfileConfigManager()
            for profile in profile_manager.list_profiles():
                console.print(f"  - {profile}")

            # Exit with error
            ctx.exit(1)
    # If no command was invoked or help is requested, show our custom help
    if ctx.invoked_subcommand is None or help_flag:
        # Get active client
        active_target = client_config_manager.get_active_target()

        print_logo()
        # Display active client information and main help
        if active_target:
            console.print(f"[bold magenta]Active target:[/] [yellow]{active_target}[/]")
        else:
            console.print("[bold red]No active target set![/] Please run 'mcpm target set <target>' to set one.")
        console.print("")

        # Display usage info
        console.print("[bold green]Usage:[/] [white]mcpm [OPTIONS] COMMAND [ARGS]...[/]")
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

        commands_table.add_row("[yellow]work target[/]")
        commands_table.add_row("  [cyan]target[/]", "Manage the active MCPM target.")

        commands_table.add_row("[yellow]client[/]")
        commands_table.add_row("  [cyan]client[/]", "Manage supported MCPM clients.")

        commands_table.add_row("[yellow]server[/]")
        commands_table.add_row("  [cyan]search[/]", "Search available MCP servers.")
        commands_table.add_row("  [cyan]info[/]", "Show detailed information about a specific MCP server.")
        commands_table.add_row("  [cyan]add[/]", "Add an MCP server directly to a client/profile.")
        commands_table.add_row("  [cyan]import[/]", "Import a custom MCP server to a client/profile.")
        commands_table.add_row("  [cyan]cp[/]", "Copy a server from one client/profile to another.")
        commands_table.add_row("  [cyan]mv[/]", "Move a server from one client/profile to another.")
        commands_table.add_row("  [cyan]rm[/]", "Remove an installed MCP server.")
        commands_table.add_row("  [cyan]ls[/]", "List all installed MCP servers.")
        commands_table.add_row("  [cyan]stash[/]", "Temporarily store a server configuration aside.")
        commands_table.add_row("  [cyan]pop[/]", "Restore a previously stashed server configuration.")
        commands_table.add_row("  [cyan]share[/]", "Share a single MCP server through a tunnel.")

        commands_table.add_row("[yellow]profile[/]")
        commands_table.add_row("  [cyan]profile[/]", "Manage MCPM profiles.")

        commands_table.add_row("[yellow]router[/]")
        commands_table.add_row("  [cyan]router[/]", "Manage MCP router service.")

        commands_table.add_row("[yellow]util[/]")
        commands_table.add_row("  [cyan]config[/]", "Manage MCPM configuration.")
        commands_table.add_row("  [cyan]inspector[/]", "Launch the MCPM Inspector UI to examine servers.")
        console.print(commands_table)

        # Additional helpful information
        console.print("")
        console.print("[italic]Run [bold]mcpm COMMAND -h[/] for more information on a command.[/]")


# Register commands
main.add_command(search.search)
main.add_command(info.info)
main.add_command(remove.remove, name="rm")
main.add_command(add.add)
main.add_command(list.list, name="ls")

main.add_command(stash.stash)
main.add_command(pop.pop)

main.add_command(target.target)
main.add_command(client.client)
main.add_command(config.config)
main.add_command(inspector.inspector, name="inspector")
main.add_command(profile.profile, name="profile")
main.add_command(transfer.move, name="mv")
main.add_command(transfer.copy, name="cp")
main.add_command(router.router, name="router")
main.add_command(custom.import_server, name="import")
main.add_command(share)

if __name__ == "__main__":
    main()
