"""
Edit command for MCPM (formerly config)
"""

import os
import json
import click
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from mcpm.utils.client_registry import ClientRegistry

console = Console()


@click.command()
def edit():
    """View or edit the active MCP client's configuration file.

    The edit command operates on the currently active MCP client (set via 'mcpm client').
    By default, this is Claude Desktop, but can be changed to other supported clients.

    The command will automatically display the config file content when it exists,
    and offer to create it when it doesn't exist. You'll also be prompted if you
    want to open the file in your default editor.

    Examples:
        mcpm edit  # Show current client's config file and offer to edit it
    """
    # Get the active client manager and related information
    client_manager = ClientRegistry.get_active_client_manager()
    client = ClientRegistry.get_active_client()
    client_info = ClientRegistry.get_client_info(client)
    client_name = client_info.get("name", client)

    # Check if client is supported
    if client_manager is None:
        console.print("[bold red]Error:[/] Unsupported active client")
        console.print("Please switch to a supported client using 'mcpm client <client-name>'")
        return

    # Get the client config file path
    config_path = client_manager.config_path

    # Check if the client is installed
    if not client_manager.is_client_installed():
        console.print(f"[bold red]Error:[/] {client_name} installation not detected.")
        return

    # Check if config file exists
    config_exists = os.path.exists(config_path)

    # Display the config file information
    console.print(f"[bold]{client_name} config file:[/] {config_path}")
    console.print(f"[bold]Status:[/] {'[green]Exists[/]' if config_exists else '[yellow]Does not exist[/]'}\n")

    # Create config file if it doesn't exist and user confirms
    if not config_exists:
        console.print(f"[bold yellow]Creating new {client_name} config file...[/]")

        # Create a basic config template
        basic_config = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": [
                        "-y",
                        "@modelcontextprotocol/server-filesystem",
                        os.path.expanduser("~/Desktop"),
                        os.path.expanduser("~/Downloads"),
                    ],
                }
            }
        }

        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)

        # Write the template to file
        try:
            with open(config_path, "w") as f:
                json.dump(basic_config, f, indent=2)
            console.print("[green]Successfully created config file![/]\n")
            config_exists = True
        except Exception as e:
            console.print(f"[bold red]Error creating config file:[/] {str(e)}")
            return

    # Show the current configuration if it exists
    if config_exists:
        try:
            with open(config_path, "r") as f:
                config_content = f.read()

            # Display the content
            console.print("[bold]Current configuration:[/]")
            panel = Panel(config_content, title=f"{client_name} Config", expand=False)
            console.print(panel)

            # Count the configured servers
            try:
                config_json = json.loads(config_content)
                server_count = len(config_json.get("mcpServers", {}))
                console.print(f"[bold]Configured servers:[/] {server_count}")

                # Display detailed information for each server
                if server_count > 0:
                    console.print("\n[bold]MCP Server Details:[/]")
                    for server_name, server_config in config_json.get("mcpServers", {}).items():
                        console.print(f"\n[bold cyan]{server_name}[/]")
                        console.print(f"  Command: [green]{server_config.get('command', 'N/A')}[/]")

                        # Display arguments
                        args = server_config.get("args", [])
                        if args:
                            console.print("  Arguments:")
                            for i, arg in enumerate(args):
                                console.print(f"    {i}: [yellow]{arg}[/]")

                        # Display environment variables
                        env_vars = server_config.get("env", {})
                        if env_vars:
                            console.print("  Environment Variables:")
                            for key, value in env_vars.items():
                                console.print(f'    [bold blue]{key}[/] = [green]"{value}"[/]')
                        else:
                            console.print("  Environment Variables: [italic]None[/]")

                        # Add a separator line
                        console.print("  " + "-" * 50)

            except json.JSONDecodeError:
                console.print("[yellow]Warning: Config file contains invalid JSON[/]")

        except Exception as e:
            console.print(f"[bold red]Error reading config file:[/] {str(e)}")

    # Prompt to edit if file exists
    should_edit = False
    if config_exists:
        should_edit = Confirm.ask("Would you like to open this file in your default editor?")

    # Open in default editor if requested
    if should_edit and config_exists:
        try:
            console.print("[bold green]Opening config file in your default editor...[/]")

            # Use appropriate command based on platform
            if os.name == "nt":  # Windows
                os.startfile(config_path)
            elif os.name == "posix":  # macOS and Linux
                subprocess.run(["open", config_path] if os.uname().sysname == "Darwin" else ["xdg-open", config_path])

            console.print(f"[italic]After editing, {client_name} must be restarted for changes to take effect.[/]")
        except Exception as e:
            console.print(f"[bold red]Error opening editor:[/] {str(e)}")
            console.print(f"You can manually edit the file at: {config_path}")
