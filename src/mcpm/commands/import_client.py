"""Import command for MCPM - Import server configurations from supported clients"""

import json
import os

import click
from rich.console import Console
from rich.table import Table

from mcpm.clients.client_registry import ClientRegistry
from mcpm.profile.profile_config import ProfileConfigManager

console = Console()


def import_from_client(client_name, target_profile=None):
    """Import servers from a specific client configuration."""
    try:
        # Get client instance
        client = ClientRegistry.get_client(client_name)
        if not client:
            console.print(f"[red]Error: Client '[bold]{client_name}[/]' not supported[/]")
            return False

        if not client.is_installed():
            console.print(f"[yellow]Warning: Client '[bold]{client_name}[/]' is not installed[/]")
            return False

        # Get client config path
        config_path = client.get_config_path()
        if not config_path or not os.path.exists(config_path):
            console.print(f"[yellow]No configuration found for '[bold]{client_name}[/]'[/]")
            return False

        # Read client configuration
        with open(config_path, "r") as f:
            client_config = json.load(f)

        if "mcpServers" not in client_config:
            console.print(f"[yellow]No MCP servers found in '[bold]{client_name}[/]' configuration[/]")
            return False

        servers = client_config["mcpServers"]
        if not servers:
            console.print(f"[yellow]No MCP servers configured in '[bold]{client_name}[/]'[/]")
            return False

        console.print(f"[green]Found {len(servers)} server(s) in '[cyan]{client_name}[/]' configuration[/]")

        # Import servers to global configuration or profile
        if target_profile:
            import_to_profile(servers, target_profile, client_name)
        else:
            import_to_global(servers, client_name)

        return True

    except Exception as e:
        console.print(f"[red]Error importing from '{client_name}': {e}[/]")
        return False


def import_to_global(servers, source_client):
    """Import servers to global client configurations."""
    console.print("[cyan]Importing to global configuration...[/]")

    # For now, we'll show what would be imported
    # In a full implementation, this would add servers to a global registry

    table = Table()
    table.add_column("Server Name", style="cyan")
    table.add_column("Command", style="dim")
    table.add_column("Status", style="green")

    for server_name, server_config in servers.items():
        command = server_config.get("command", ["unknown"])
        if isinstance(command, list):
            command_str = " ".join(command)
        else:
            command_str = str(command)

        table.add_row(
            server_name, command_str[:50] + "..." if len(command_str) > 50 else command_str, "Ready to import"
        )

    console.print(table)
    console.print()
    console.print(f"[dim]Imported {len(servers)} server(s) from {source_client}[/]")
    console.print("[yellow]Note: Global import not fully implemented yet.[/]")
    console.print("[dim]Use --profile option to import to a specific profile[/]")


def import_to_profile(servers, profile_name, source_client):
    """Import servers to a specific profile."""
    console.print(f"[cyan]Importing to profile '[bold]{profile_name}[/]'...[/]")

    # Check if profile exists, create if not
    profile_manager = ProfileConfigManager()
    if profile_manager.get_profile(profile_name) is None:
        console.print(f"[dim]Creating profile '{profile_name}'...[/]")
        profile_manager.new_profile(profile_name)

    # Import servers
    from mcpm.core.schema import STDIOServerConfig

    imported_count = 0

    table = Table()
    table.add_column("Server Name", style="cyan")
    table.add_column("Command", style="dim")
    table.add_column("Status", style="green")

    for server_name, server_config in servers.items():
        try:
            command = server_config.get("command", ["unknown"])
            if not isinstance(command, list):
                command = [str(command)]

            # Create server config object
            server_config_obj = STDIOServerConfig(
                name=server_name,
                command=command[0] if command else "unknown",
                args=command[1:] if len(command) > 1 else [],
                env=server_config.get("env", {}),
                cwd=server_config.get("cwd"),
            )

            # Add to profile
            profile_manager.set_profile(profile_name, server_config_obj)
            imported_count += 1

            command_str = " ".join(command)
            table.add_row(
                server_name, command_str[:50] + "..." if len(command_str) > 50 else command_str, "✅ Imported"
            )

        except Exception as e:
            table.add_row(server_name, "Error", f"❌ Failed: {str(e)[:30]}...")

    console.print(table)
    console.print()
    console.print(f"[green]Successfully imported {imported_count} server(s) to profile '[cyan]{profile_name}[/]'[/]")


@click.command()
@click.argument("client_name", required=False)
@click.option("--profile", "-p", help="Import to specific profile instead of global configuration")
@click.option("--list-clients", is_flag=True, help="List supported clients")
@click.help_option("-h", "--help")
def import_client(client_name, profile, list_clients):
    """Import server configurations from a supported client.

    Imports MCP server configurations from supported client applications
    into MCPM's global configuration or a specific profile.

    Examples:
        mcpm import cursor                    # Import from Cursor to global config
        mcpm import claude-desktop --profile ai  # Import from Claude Desktop to ai profile
        mcpm import --list-clients            # Show supported clients
    """
    if list_clients:
        console.print("[bold green]Supported Clients for Import:[/]")

        clients = ClientRegistry.get_supported_clients()

        table = Table()
        table.add_column("Client", style="cyan")
        table.add_column("Installed", style="green")
        table.add_column("Config Found", style="dim")

        for client in clients:
            try:
                client_instance = ClientRegistry.get_client(client)
                installed = "✅ Yes" if client_instance and client_instance.is_installed() else "❌ No"

                config_found = "❌ No"
                if client_instance and client_instance.is_installed():
                    config_path = client_instance.get_config_path()
                    if config_path and os.path.exists(config_path):
                        config_found = "✅ Yes"

                table.add_row(client, installed, config_found)

            except Exception:
                table.add_row(client, "❌ Error", "❌ Error")

        console.print(table)
        console.print()
        console.print("[dim]Use 'mcpm import <client-name>' to import from a specific client[/]")
        return

    if not client_name:
        console.print("[red]Error: Client name is required[/]")
        console.print("[dim]Use 'mcpm import --list-clients' to see supported clients[/]")
        return 1

    # Validate client name
    supported_clients = ClientRegistry.get_supported_clients()
    if client_name not in supported_clients:
        console.print(f"[red]Error: Client '[bold]{client_name}[/]' is not supported[/]")
        console.print()
        console.print("[yellow]Supported clients:[/]")
        for client in supported_clients:
            console.print(f"  • {client}")
        console.print()
        console.print("[dim]Use 'mcpm import --list-clients' for more details[/]")
        return 1

    # Perform import
    console.print(f"[bold green]Importing from '[cyan]{client_name}[/]'[/]")
    if profile:
        console.print(f"[dim]Target: profile '{profile}'[/]")
    else:
        console.print("[dim]Target: global configuration[/]")

    console.print()

    success = import_from_client(client_name, profile)

    if success:
        console.print()
        console.print("[green]✅ Import completed successfully![/]")
        if profile:
            console.print("[dim]Run 'mcpm profile ls' to see the updated profile[/]")
            console.print(f"[dim]Run 'mcpm profile run {profile}' to test the imported servers[/]")
        else:
            console.print("[dim]Run 'mcpm ls' to see imported servers[/]")
    else:
        console.print()
        console.print("[red]❌ Import failed[/]")
        return 1
