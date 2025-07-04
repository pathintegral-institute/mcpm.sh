"""
Client command for MCPM
"""

import json
import os
import subprocess

import click
from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console
from rich.table import Table

from mcpm.clients.client_config import ClientConfigManager
from mcpm.clients.client_registry import ClientRegistry
from mcpm.global_config import GlobalConfigManager
from mcpm.utils.display import print_error

console = Console()
client_config_manager = ClientConfigManager()
global_config_manager = GlobalConfigManager()


@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
def client():
    """Manage MCP client configurations and MCPM server integrations.

    Commands for listing clients and managing which MCPM servers are enabled
    in specific MCP client configurations.

    Examples:

    \b
        mcpm client ls                    # List all supported MCP clients and their status
        mcpm client edit cursor           # Interactive server selection for Cursor
        mcpm client edit claude-desktop   # Interactive server selection for Claude Desktop
        mcpm client edit cursor -e        # Open Cursor config in external editor
    """
    pass


@client.command(name="ls", context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("--verbose", "-v", is_flag=True, help="Show detailed server information")
def list_clients(verbose):
    """List all supported MCP clients and their enabled MCPM servers."""
    # Get the list of supported clients
    supported_clients = ClientRegistry.get_supported_clients()
    installed_clients = ClientRegistry.detect_installed_clients()
    active_client = ClientRegistry.get_active_client()

    # Count total clients
    total_clients = len(supported_clients)
    installed_count = sum(1 for c in supported_clients if installed_clients.get(c, False))
    
    console.print(f"\n[green]Found {installed_count} MCP client(s)[/]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("MCPM Servers", overflow="fold")
    table.add_column("Other Servers", overflow="fold")
    if verbose:
        table.add_column("Server Details", overflow="fold")

    # Separate installed and uninstalled clients
    installed_client_names = [c for c in supported_clients if installed_clients.get(c, False)]
    uninstalled_client_names = [c for c in supported_clients if not installed_clients.get(c, False)]
    
    # Process only installed clients in the table
    for client_name in sorted(installed_client_names):
        # Get client info
        client_info = ClientRegistry.get_client_info(client_name)
        display_name = client_info.get("name", client_name)
        
        # Build client name with code and status indicators
        name_parts = [f"{display_name} [dim]({client_name})[/]"]
            
        if client_name == active_client:
            name_parts.append("[bold green]ACTIVE[/]")
            
        client_display = " ".join(name_parts)
        
        # Get the client manager to check MCPM servers
        client_manager = ClientRegistry.get_client_manager(client_name)
        if not client_manager:
            row = [client_display, "[dim]Cannot read config[/]", "[dim]Cannot read config[/]"]
            if verbose:
                row.append("[dim]-[/]")
            table.add_row(*row)
            continue
            
        # Find MCPM-managed servers and other servers in the client config
        mcpm_servers = []
        other_servers = []
        mcpm_server_details = []
        
        try:
            client_servers = client_manager.get_servers()
            for server_name, server_config in client_servers.items():
                # Check if this is an MCPM-managed server
                # Look for servers using 'mcpm run' command or with mcpm_ prefix
                is_mcpm_server = False
                actual_server_name = None
                
                # Handle both object attributes and dictionary keys
                if hasattr(server_config, "command"):
                    command = server_config.command
                    args = getattr(server_config, "args", [])
                elif isinstance(server_config, dict):
                    command = server_config.get("command", "")
                    args = server_config.get("args", [])
                else:
                    continue
                
                if command == "mcpm":
                    if len(args) >= 2 and args[0] == "run":
                        is_mcpm_server = True
                        actual_server_name = args[1]
                elif server_name.startswith("mcpm_"):
                    # Check if it's using mcpm run command
                    if command == "mcpm":
                        if len(args) >= 2 and args[0] == "run":
                            is_mcpm_server = True
                            actual_server_name = args[1]
                            
                if is_mcpm_server and actual_server_name:
                    mcpm_servers.append(actual_server_name)
                    
                    if verbose:
                        # Get the actual server config from global config for details
                        global_server = global_config_manager.get_server(actual_server_name)
                        if global_server:
                            if hasattr(global_server, "command"):
                                cmd_args = " ".join(global_server.args or [])
                                mcpm_server_details.append(f"{actual_server_name}: {global_server.command} {cmd_args}")
                            elif hasattr(global_server, "url"):
                                mcpm_server_details.append(f"{actual_server_name}: {global_server.url}")
                            else:
                                mcpm_server_details.append(f"{actual_server_name}: Custom")
                        else:
                            mcpm_server_details.append(f"{actual_server_name}: [dim]Not in global config[/]")
                else:
                    # This is a non-MCPM server
                    other_servers.append(server_name)
                            
        except Exception as e:
            # If we can't read the client config, note it
            row = [client_display, "[red]Error reading config[/]", "[red]Error reading config[/]"]
            if verbose:
                row.append("[dim]-[/]")
            table.add_row(*row)
            continue
        
        # Format server lists
        if mcpm_servers:
            mcpm_display = ", ".join(mcpm_servers)
            detail_display = "\n".join(mcpm_server_details) if verbose and mcpm_server_details else None
        else:
            mcpm_display = "[dim]None[/]"
            detail_display = "[dim]-[/]" if verbose else None
            
        if other_servers:
            other_display = ", ".join(other_servers)
        else:
            other_display = "[dim]None[/]"
        
        # Add row
        row = [client_display, mcpm_display, other_display]
        if verbose:
            row.append(detail_display or "[dim]-[/]")
        table.add_row(*row)

    console.print(table)
    console.print()
    
    # Show uninstalled clients in compact format
    if uninstalled_client_names:
        uninstalled_display_names = []
        for client_name in sorted(uninstalled_client_names):
            client_info = ClientRegistry.get_client_info(client_name)
            display_name = client_info.get("name", client_name)
            uninstalled_display_names.append(display_name)
        
        console.print(f"[dim]Additional supported clients (not detected): {', '.join(uninstalled_display_names)}[/]")
        console.print()
        
    console.print("[dim]Tips:[/]")
    console.print("[dim]  • Use 'mcpm client edit <client>' to enable/disable MCPM servers in a client[/]")
    console.print("[dim]  • Use 'mcpm client edit <client> -e' to open client config in your default editor[/]\n")


@client.command(name="edit", context_settings=dict(help_option_names=["-h", "--help"]))
@click.argument("client_name")
@click.option("-e", "--external", is_flag=True, help="Open config file in external editor instead of interactive mode")
def edit_client(client_name, external):
    """Enable/disable MCPM-managed servers in the specified client configuration.

    This command provides an interactive interface to integrate MCPM-managed
    servers into your MCP client by adding or removing 'mcpm run {server}'
    entries in the client config. Uses checkbox selection for easy management.

    Use --external/-e to open the config file directly in your default editor
    instead of using the interactive interface.

    CLIENT_NAME is the name of the MCP client to configure (e.g., cursor, claude-desktop, windsurf).
    """
    # Get the client manager for the specified client
    client_manager = ClientRegistry.get_client_manager(client_name)
    if client_manager is None:
        console.print(f"[red]Error: Client '{client_name}' is not supported.[/]")
        console.print("[yellow]Available clients:[/]")
        supported_clients = ClientRegistry.get_supported_clients()
        for supported_client in sorted(supported_clients):
            console.print(f"  [cyan]{supported_client}[/]")
        return

    client_info = ClientRegistry.get_client_info(client_name)
    display_name = client_info.get("name", client_name)

    # Check if the client is installed
    if not client_manager.is_client_installed():
        print_error(f"{display_name} installation not detected.")
        return

    # Get the client config file path
    config_path = client_manager.config_path
    config_exists = os.path.exists(config_path)

    console.print(f"[bold]{display_name} Configuration Management[/]")
    console.print(f"[dim]Config file: {config_path}[/]\n")

    # If external editor requested, handle that directly
    if external:
        # Ensure config file exists before opening
        if not config_exists:
            console.print("[yellow]Config file does not exist. Creating basic config...[/]")
            _create_basic_config(config_path)

        _open_in_editor(config_path, display_name)
        return

    # Load current client configuration
    current_config = {}
    mcpm_servers = set()  # Servers currently managed by MCPM in client config

    if config_exists:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                current_config = json.load(f)

            # Find servers currently using 'mcpm run' (with mcpm_ prefix)
            mcp_servers = current_config.get("mcpServers", {})
            for client_server_name, server_config in mcp_servers.items():
                command = server_config.get("command", "")
                args = server_config.get("args", [])

                # Check if this is an MCPM-managed server (prefixed with mcpm_)
                if client_server_name.startswith("mcpm_") and (
                    command == "mcpm" and len(args) >= 2 and args[0] == "run"
                ):
                    if len(args) >= 2 and args[0] == "run":
                        # Remove mcpm_ prefix to get actual server name
                        actual_server_name = args[1]
                        mcpm_servers.add(actual_server_name)

        except (json.JSONDecodeError, FileNotFoundError) as e:
            console.print(f"[yellow]Warning: Could not read existing config: {e}[/]")

    # Get all MCPM global servers
    global_servers = global_config_manager.list_servers()

    if not global_servers:
        console.print("[yellow]No servers found in MCPM global configuration.[/]")
        console.print("[dim]Install servers first using: mcpm install <server>[/]")
        return

    # Display current status
    console.print("[bold]MCPM-Managed Servers:[/]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Server Name", style="cyan")
    table.add_column("Status in Client", style="yellow")
    table.add_column("Description", style="white")

    for server_name, server_config in global_servers.items():
        status = "[green]Enabled[/]" if server_name in mcpm_servers else "[red]Disabled[/]"
        description = getattr(server_config, "description", "No description") or "No description"
        table.add_row(server_name, status, description[:50] + "..." if len(description) > 50 else description)

    console.print(table)
    console.print()

    # Use InquirerPy for interactive server selection
    _interactive_server_selection_inquirer(
        client_manager, config_path, current_config, mcpm_servers, global_servers, display_name
    )


def _interactive_server_selection_inquirer(
    client_manager, config_path, current_config, mcpm_servers, global_servers, client_name
):
    """Interactive server selection using InquirerPy with checkboxes."""
    try:
        # Build choices with current status
        server_choices = []
        for server_name in sorted(global_servers.keys()):
            server_config = global_servers[server_name]
            # Get server description for display
            description = getattr(server_config, "description", "No description") or "No description"

            # Show server name and description
            choice_name = f"{server_name} - {description[:40]}" + ("..." if len(description) > 40 else "")

            # Set enabled=True only for servers currently in the client config
            is_currently_enabled = server_name in mcpm_servers
            server_choices.append(Choice(value=server_name, name=choice_name, enabled=is_currently_enabled))

        if not server_choices:
            console.print("[yellow]No MCPM servers available to configure.[/]")
            return

        # Use InquirerPy checkbox for selection
        console.print(f"\n[bold]Select servers to enable in {client_name}:[/]")
        console.print("[dim]Use space to toggle, enter to confirm, ESC to cancel[/]")

        selected_servers = inquirer.checkbox(
            message="Select servers to enable:", choices=server_choices, keybindings={"interrupt": [{"key": "escape"}]}
        ).execute()

        if selected_servers is None:
            console.print("[yellow]Operation cancelled.[/]")
            return

        # Convert to set for comparison
        new_mcpm_servers = set(selected_servers)

        # Check if changes were made
        if new_mcpm_servers == mcpm_servers:
            console.print("[yellow]No changes made.[/]")
            return

        # Save the updated configuration
        _save_config_with_mcpm_servers(client_manager, config_path, current_config, new_mcpm_servers, client_name)

        # Show what changed
        added = new_mcpm_servers - mcpm_servers
        removed = mcpm_servers - new_mcpm_servers

        if added:
            console.print(f"[green]Enabled: {', '.join(sorted(added))}[/]")
        if removed:
            console.print(f"[red]Disabled: {', '.join(sorted(removed))}[/]")

        # Inform about external editor option
        console.print(
            "\n[dim]Tip: Use 'mcpm client edit {client_name} -e' to open config directly in your editor.[/]".format(
                client_name=client_name.replace(" ", "-")
            )
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled.[/]")
    except Exception as e:
        console.print(f"[red]Error running interactive selection: {e}[/]")


def _save_config_with_mcpm_servers(client_manager, config_path, current_config, mcpm_servers, client_name):
    """Save the client config with updated MCPM server entries using the client manager."""
    try:
        from mcpm.core.schema import STDIOServerConfig
        
        # Get list of current servers
        current_server_list = client_manager.list_servers()
        
        # Remove existing MCPM-managed entries (those with mcpm_ prefix)
        servers_to_remove = []
        for server_name in current_server_list:
            if server_name.startswith("mcpm_"):
                # Check if it's actually an MCPM server by getting its config
                server_config = client_manager.get_server(server_name)
                if server_config and hasattr(server_config, "command") and server_config.command == "mcpm":
                    args = getattr(server_config, "args", [])
                    if len(args) >= 2 and args[0] == "run":
                        servers_to_remove.append(server_name)

        # Remove old MCPM servers
        for server_name in servers_to_remove:
            client_manager.remove_server(server_name)

        # Add new MCPM-managed entries with mcpm_ prefix
        for server_name in mcpm_servers:
            prefixed_name = f"mcpm_{server_name}"
            # Create a proper ServerConfig object for MCPM server
            server_config = STDIOServerConfig(
                name=prefixed_name,
                command="mcpm",
                args=["run", server_name]
            )
            client_manager.add_server(server_config)

        console.print(f"[green]Successfully updated {client_name} configuration![/]")
        console.print(f"[dim]Config saved to: {config_path}[/]")
        console.print(f"[italic]Restart {client_name} for changes to take effect.[/]")

    except Exception as e:
        print_error("Error saving configuration", str(e))


def _create_basic_config(config_path):
    """Create a basic MCP client config file."""
    basic_config = {"mcpServers": {}}

    # Create the directory if it doesn't exist
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    # Write the basic config to file
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(basic_config, f, indent=2)
        console.print("[green]Basic config file created successfully![/]")
    except Exception as e:
        print_error("Error creating config file", str(e))
        raise


def _open_in_editor(config_path, client_name):
    """Open the config file in the default editor."""
    try:
        console.print("[bold green]Opening config file in your default editor...[/]")

        # Use appropriate command based on platform
        if os.name == "nt":  # Windows
            os.startfile(config_path)
        elif os.name == "posix":  # macOS and Linux
            subprocess.run(["open", config_path] if os.uname().sysname == "Darwin" else ["xdg-open", config_path])

        console.print(f"[italic]After editing, {client_name} must be restarted for changes to take effect.[/]")
    except Exception as e:
        print_error("Error opening editor", str(e))
        console.print(f"You can manually edit the file at: {config_path}")
