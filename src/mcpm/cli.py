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
    inspector,
    list,
    pop,
    profile,
    remove,
    router,
    search,
    stash,
    transfer,
)

console = Console()
client_config_manager = ClientConfigManager()

# Set -h as an alias for --help but we'll handle it ourselves
CONTEXT_SETTINGS = dict(help_option_names=[])


@click.group(context_settings=CONTEXT_SETTINGS, invoke_without_command=True)
@click.option("-h", "--help", "help_flag", is_flag=True, help="Show this message and exit.")
@click.version_option(version=__version__)
@click.pass_context
def main(ctx, help_flag):
    """MCPM - Model Context Protocol Manager.

    A tool for managing MCP servers across various clients.
    """
    # Check if a command is being executed (and it's not help, no command, or the client command)
    if ctx.invoked_subcommand and ctx.invoked_subcommand != "client" and not help_flag:
        # Check if active client is set
        active_client = client_config_manager.get_active_client()
        if not active_client:
            console.print("[bold red]Error:[/] No active client set.")
            console.print("Please run 'mcpm client <client-name>' to set an active client.")
            console.print("Available clients:")

            # Show available clients
            from mcpm.clients.client_registry import ClientRegistry

            for client in ClientRegistry.get_supported_clients():
                console.print(f"  - {client}")

            # Exit with error
            ctx.exit(1)
    # If no command was invoked or help is requested, show our custom help
    if ctx.invoked_subcommand is None or help_flag:
        # Get active client
        active_client = client_config_manager.get_active_client()

        # Create a nice ASCII art banner with proper alignment using Rich
        from rich.panel import Panel

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
            "Model Context Protocol Manager",
            "Open Source. Forever Free.",
            "Built with ❤️ by [bold cyan]Path Integral Institute[/]",
        ]

        # No need to convert to joined string since we're formatting directly in the panel

        # Create a panel with styled content
        panel = Panel(
            f"[bold green]{logo[0]}\n{logo[1]}\n{logo[2]}\n{logo[3]}\n{logo[4]}\n{logo[5]}[/]\n\n[bold yellow]{logo[7]}[/] [italic blue]{logo[8]}[/]\n[bold magenta]{logo[9]}[/]\n[bold cyan]{logo[10]}[/]",
            border_style="bold cyan",
            expand=False,
            padding=(0, 2),
        )

        # Print the panel
        console.print(panel)

        # Get information about installed clients
        from mcpm.clients.client_registry import ClientRegistry

        installed_clients = ClientRegistry.detect_installed_clients()

        # Display active client information and main help
        if active_client:
            client_status = "[green]✓[/]" if installed_clients.get(active_client, False) else "[yellow]⚠[/]"
            console.print(f"[bold magenta]Active client:[/] [yellow]{active_client}[/] {client_status}")
        else:
            console.print("[bold red]No active client set![/] Please run 'mcpm client <client-name>' to set one.")
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
        commands_table.add_row("[yellow]client[/]")
        commands_table.add_row("  [cyan]client[/]", "Manage the active MCPM client.")

        commands_table.add_row("[yellow]server[/]")
        commands_table.add_row("  [cyan]search[/]", "Search available MCP servers.")
        commands_table.add_row("  [cyan]add[/]", "Add an MCP server directly to a client.")
        commands_table.add_row("  [cyan]cp[/]", "Copy a server from one client/profile to another.")
        commands_table.add_row("  [cyan]mv[/]", "Move a server from one client/profile to another.")
        commands_table.add_row("  [cyan]rm[/]", "Remove an installed MCP server.")
        commands_table.add_row("  [cyan]ls[/]", "List all installed MCP servers.")
        commands_table.add_row("  [cyan]stash[/]", "Temporarily store a server configuration aside.")
        commands_table.add_row("  [cyan]pop[/]", "Restore a previously stashed server configuration.")

        commands_table.add_row("[yellow]profile[/]")
        commands_table.add_row("  [cyan]profile[/]", "Manage MCPM profiles.")
        commands_table.add_row("  [cyan]activate[/]", "Activate a profile.")
        commands_table.add_row("  [cyan]deactivate[/]", "Deactivate a profile.")

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
main.add_command(remove.remove, name="rm")
main.add_command(add.add)
main.add_command(list.list, name="ls")

main.add_command(stash.stash)
main.add_command(pop.pop)

main.add_command(client.client)
main.add_command(config.config)
main.add_command(inspector.inspector, name="inspector")
main.add_command(profile.profile, name="profile")
main.add_command(transfer.move, name="mv")
main.add_command(transfer.copy, name="cp")
main.add_command(profile.activate)
main.add_command(profile.deactivate)
main.add_command(router.router, name="router")

if __name__ == "__main__":
    main()
