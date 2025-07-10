"""
Edit command for modifying server configurations
"""

import os
import shlex
import subprocess
import sys
from typing import Any, Dict, Optional

from InquirerPy import inquirer
from rich.console import Console
from rich.table import Table

from mcpm.core.schema import RemoteServerConfig, STDIOServerConfig
from mcpm.global_config import GlobalConfigManager
from mcpm.utils.display import print_error
from mcpm.utils.rich_click_config import click

console = Console()
global_config_manager = GlobalConfigManager()


@click.command(name="edit", context_settings=dict(help_option_names=["-h", "--help"]))
@click.argument("server_name", required=False)
@click.option("-N", "--new", is_flag=True, help="Create a new server configuration")
@click.option("-e", "--editor", is_flag=True, help="Open global config in external editor")
def edit(server_name, new, editor):
    """Edit a server configuration.

    Opens an interactive form editor that allows you to:
    - Change the server name with real-time validation
    - Modify server-specific properties (command, args, env for STDIO; URL, headers for remote)
    - Step through each field, press Enter to confirm, ESC to cancel

    Examples:

        mcpm edit time                                    # Edit existing server
        mcpm edit agentkit                                # Edit agentkit server
        mcpm edit -N                                      # Create new server
        mcpm edit -e                                      # Open global config in editor
    """
    # Handle editor mode
    if editor:
        _open_global_config_in_editor()
        return 0

    # Handle new server mode
    if new:
        if server_name:
            print_error(
                "Cannot specify both server name and --new flag", "Use either 'mcpm edit <server>' or 'mcpm edit --new'"
            )
            raise click.ClickException("Cannot specify both server name and --new flag")
        _create_new_server()
        return 0

    # Require server name for editing existing servers
    if not server_name:
        print_error("Server name is required", "Use 'mcpm edit <server>', 'mcpm edit --new', or 'mcpm edit --editor'")
        raise click.ClickException("Server name is required")

    # Get the existing server
    server_config = global_config_manager.get_server(server_name)
    if not server_config:
        print_error(
            f"Server '{server_name}' not found",
            "Run 'mcpm ls' to see available servers or use 'mcpm edit --new' to create one",
        )
        raise click.ClickException(f"Server '{server_name}' not found")

    # Display current configuration
    console.print(f"\n[bold green]Current Configuration for '{server_name}':[/]")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Property", style="yellow")
    table.add_column("Current Value", style="white")

    table.add_row("Name", server_config.name)
    table.add_row("Type", type(server_config).__name__)

    if isinstance(server_config, STDIOServerConfig):
        table.add_row("Command", server_config.command)
        table.add_row("Arguments", " ".join(server_config.args) if server_config.args else "[dim]None[/]")
        table.add_row(
            "Environment",
            ", ".join(f"{k}={v}" for k, v in server_config.env.items()) if server_config.env else "[dim]None[/]",
        )
    elif isinstance(server_config, RemoteServerConfig):
        table.add_row("URL", server_config.url)
        table.add_row(
            "Headers",
            ", ".join(f"{k}={v}" for k, v in server_config.headers.items())
            if server_config.headers
            else "[dim]None[/]",
        )

    table.add_row(
        "Profile Tags", ", ".join(server_config.profile_tags) if server_config.profile_tags else "[dim]None[/]"
    )

    console.print(table)
    console.print()

    # Interactive mode
    console.print(f"[bold green]Opening Interactive Server Editor: [cyan]{server_name}[/]")
    console.print("[dim]Type your answers, press Enter to confirm each field, ESC to cancel[/]")
    console.print()

    try:
        result = interactive_server_edit(server_config)

        if result is None:
            console.print("[yellow]Interactive editing not available in this environment[/]")
            console.print("[dim]This command requires a terminal for interactive input[/]")
            return 1

        if result.get("cancelled", True):
            console.print("[yellow]Server editing cancelled[/]")
            return 0

        # Check if new name conflicts with existing servers (if changed)
        new_name = result["answers"]["name"]
        if new_name != server_config.name and global_config_manager.get_server(new_name):
            console.print(f"[red]Error: Server '[bold]{new_name}[/]' already exists[/]")
            return 1

        # Apply the interactive changes
        original_name = server_config.name
        if not apply_interactive_changes(server_config, result):
            console.print("[red]Failed to apply changes[/]")
            return 1

        # Save the changes
        try:
            if new_name != original_name:
                # If name changed, we need to remove old and add new
                global_config_manager.remove_server(original_name)
                global_config_manager.add_server(server_config)
                console.print(f"[green]✅ Server renamed from '[cyan]{original_name}[/]' to '[cyan]{new_name}[/]'[/]")
            else:
                # Just update in place by saving
                global_config_manager._save_servers()
                console.print(f"[green]✅ Server '[cyan]{server_name}[/]' updated successfully[/]")
        except Exception as e:
            print_error("Failed to save changes", str(e))
            raise click.ClickException(f"Failed to save changes: {e}")

        return 0

    except Exception as e:
        console.print(f"[red]Error running interactive editor: {e}[/]")
        return 1


def interactive_server_edit(server_config) -> Optional[Dict[str, Any]]:
    """Interactive server edit using InquirerPy forms."""
    # Check if we're in a terminal that supports interactive input
    if not sys.stdin.isatty():
        return None

    try:
        # Clear any remaining command line arguments to avoid conflicts
        original_argv = sys.argv[:]
        sys.argv = [sys.argv[0]]  # Keep only script name

        try:
            answers = {}

            # Server name - always editable
            answers["name"] = inquirer.text(
                message="Server name:",
                default=server_config.name,
                validate=lambda text: len(text.strip()) > 0 and not text.strip() != text.strip(),
                invalid_message="Server name cannot be empty or contain leading/trailing spaces",
                keybindings={"interrupt": [{"key": "escape"}]},
            ).execute()

            if isinstance(server_config, STDIOServerConfig):
                # STDIO Server configuration
                console.print("\n[cyan]STDIO Server Configuration[/]")

                answers["command"] = inquirer.text(
                    message="Command to execute:",
                    default=server_config.command,
                    validate=lambda text: len(text.strip()) > 0,
                    invalid_message="Command cannot be empty",
                    keybindings={"interrupt": [{"key": "escape"}]},
                ).execute()

                # Arguments as space-separated string
                current_args = " ".join(server_config.args) if server_config.args else ""
                answers["args"] = inquirer.text(
                    message="Arguments (space-separated, quotes supported):",
                    default=current_args,
                    instruction="(Leave empty for no arguments, use quotes for args with spaces)",
                    keybindings={"interrupt": [{"key": "escape"}]},
                ).execute()

                # Environment variables
                current_env = ", ".join(f"{k}={v}" for k, v in server_config.env.items()) if server_config.env else ""
                answers["env"] = inquirer.text(
                    message="Environment variables (KEY=value,KEY2=value2):",
                    default=current_env,
                    instruction="(Leave empty for no environment variables)",
                    keybindings={"interrupt": [{"key": "escape"}]},
                ).execute()

            elif isinstance(server_config, RemoteServerConfig):
                # Remote Server configuration
                console.print("\n[cyan]Remote Server Configuration[/]")

                answers["url"] = inquirer.text(
                    message="Server URL:",
                    default=server_config.url,
                    validate=lambda text: text.strip().startswith(("http://", "https://")) or text.strip() == "",
                    invalid_message="URL must start with http:// or https://",
                    keybindings={"interrupt": [{"key": "escape"}]},
                ).execute()

                # Headers
                current_headers = (
                    ", ".join(f"{k}={v}" for k, v in server_config.headers.items()) if server_config.headers else ""
                )
                answers["headers"] = inquirer.text(
                    message="HTTP headers (KEY=value,KEY2=value2):",
                    default=current_headers,
                    instruction="(Leave empty for no custom headers)",
                    keybindings={"interrupt": [{"key": "escape"}]},
                ).execute()
            else:
                console.print("[red]Cannot edit custom server configurations interactively[/]")
                return None

            # Confirmation
            console.print("\n[bold]Summary of changes:[/]")
            console.print(f"Name: [cyan]{server_config.name}[/] → [cyan]{answers['name']}[/]")

            if isinstance(server_config, STDIOServerConfig):
                console.print(f"Command: [cyan]{server_config.command}[/] → [cyan]{answers['command']}[/]")
                new_args = shlex.split(answers["args"]) if answers["args"] else []
                console.print(f"Arguments: [cyan]{server_config.args}[/] → [cyan]{new_args}[/]")

                new_env = {}
                if answers["env"]:
                    for env_pair in answers["env"].split(","):
                        if "=" in env_pair:
                            key, value = env_pair.split("=", 1)
                            new_env[key.strip()] = value.strip()
                console.print(f"Environment: [cyan]{server_config.env}[/] → [cyan]{new_env}[/]")

            elif isinstance(server_config, RemoteServerConfig):
                console.print(f"URL: [cyan]{server_config.url}[/] → [cyan]{answers['url']}[/]")

                new_headers = {}
                if answers["headers"]:
                    for header_pair in answers["headers"].split(","):
                        if "=" in header_pair:
                            key, value = header_pair.split("=", 1)
                            new_headers[key.strip()] = value.strip()
                console.print(f"Headers: [cyan]{server_config.headers}[/] → [cyan]{new_headers}[/]")

            confirm = inquirer.confirm(
                message="Apply these changes?",
                default=True,
                keybindings={"interrupt": [{"key": "escape"}]},
            ).execute()

            if not confirm:
                return {"cancelled": True}

        finally:
            # Restore original argv
            sys.argv = original_argv

        return {"cancelled": False, "answers": answers, "server_type": type(server_config).__name__}

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Operation cancelled[/]")
        return {"cancelled": True}
    except Exception as e:
        console.print(f"[red]Error running interactive form: {e}[/]")
        return None


def apply_interactive_changes(server_config, interactive_result):
    """Apply the changes from interactive editing to the server config."""
    if interactive_result.get("cancelled", True):
        return False

    answers = interactive_result["answers"]

    # Update name
    server_config.name = answers["name"].strip()

    if isinstance(server_config, STDIOServerConfig):
        # Update STDIO-specific fields
        server_config.command = answers["command"].strip()

        # Parse arguments
        if answers["args"].strip():
            server_config.args = shlex.split(answers["args"])
        else:
            server_config.args = []

        # Parse environment variables
        server_config.env = {}
        if answers["env"].strip():
            for env_pair in answers["env"].split(","):
                if "=" in env_pair:
                    key, value = env_pair.split("=", 1)
                    server_config.env[key.strip()] = value.strip()

    elif isinstance(server_config, RemoteServerConfig):
        # Update remote-specific fields
        server_config.url = answers["url"].strip()

        # Parse headers
        server_config.headers = {}
        if answers["headers"].strip():
            for header_pair in answers["headers"].split(","):
                if "=" in header_pair:
                    key, value = header_pair.split("=", 1)
                    server_config.headers[key.strip()] = value.strip()

    return True


def _open_global_config_in_editor():
    """Open the global MCPM configuration file in the default editor."""
    try:
        # Get the global config file path
        config_path = global_config_manager.config_path

        if not os.path.exists(config_path):
            console.print("[yellow]No global configuration file found.[/]")
            console.print("[dim]Install a server first with 'mcpm install <server>' to create the config file.[/]")
            return

        console.print("[bold green]Opening global MCPM configuration in your default editor...[/]")

        # Use appropriate command based on platform
        if os.name == "nt":  # Windows
            os.startfile(config_path)
        elif os.name == "posix":  # macOS and Linux
            subprocess.run(["open", config_path] if os.uname().sysname == "Darwin" else ["xdg-open", config_path])

        console.print(f"[italic]Global config file: {config_path}[/]")
        console.print("[dim]After editing, restart any running MCP servers for changes to take effect.[/]")
    except Exception as e:
        print_error("Error opening editor", str(e))
        console.print(f"You can manually edit the file at: {config_path}")


def _create_new_server():
    """Create a new server configuration interactively."""
    console.print("[bold green]Create New Server Configuration[/]")
    console.print("[dim]Type your answers, press Enter to confirm each field, ESC to cancel[/]")
    console.print()

    try:
        result = _interactive_new_server_form()

        if result is None:
            console.print("[yellow]Interactive editing not available in this environment[/]")
            console.print("[dim]This command requires a terminal for interactive input[/]")
            return 1

        if result.get("cancelled", True):
            console.print("[yellow]Server creation cancelled[/]")
            return 0

        # Check if server name already exists
        server_name = result["answers"]["name"]
        if global_config_manager.get_server(server_name):
            console.print(f"[red]Error: Server '[bold]{server_name}[/]' already exists[/]")
            return 1

        # Create the server config based on type
        server_type = result["answers"]["type"]
        if server_type == "stdio":
            server_config = STDIOServerConfig(
                name=server_name,
                command=result["answers"]["command"],
                args=shlex.split(result["answers"]["args"]) if result["answers"]["args"] else [],
                env={},
            )

            # Parse environment variables
            if result["answers"]["env"]:
                for env_pair in result["answers"]["env"].split(","):
                    if "=" in env_pair:
                        key, value = env_pair.split("=", 1)
                        server_config.env[key.strip()] = value.strip()
        else:  # remote
            server_config = RemoteServerConfig(name=server_name, url=result["answers"]["url"], headers={})

            # Parse headers
            if result["answers"]["headers"]:
                for header_pair in result["answers"]["headers"].split(","):
                    if "=" in header_pair:
                        key, value = header_pair.split("=", 1)
                        server_config.headers[key.strip()] = value.strip()

        # Save the new server
        try:
            global_config_manager.add_server(server_config)
            console.print(f"[green]✅ Successfully created server '[cyan]{server_name}[/]'[/]")
        except Exception as e:
            print_error("Failed to save new server", str(e))
            raise click.ClickException(f"Failed to save new server: {e}")

        return 0

    except Exception as e:
        console.print(f"[red]Error creating new server: {e}[/]")
        return 1


def _interactive_new_server_form() -> Optional[Dict[str, Any]]:
    """Interactive form for creating a new server."""
    # Check if we're in a terminal that supports interactive input
    if not sys.stdin.isatty():
        return None

    try:
        # Clear any remaining command line arguments to avoid conflicts
        original_argv = sys.argv[:]
        sys.argv = [sys.argv[0]]  # Keep only script name

        try:
            answers = {}

            # Server name - required
            answers["name"] = inquirer.text(
                message="Server name:",
                validate=lambda text: len(text.strip()) > 0 and not text.strip() != text.strip(),
                invalid_message="Server name cannot be empty or contain leading/trailing spaces",
                keybindings={"interrupt": [{"key": "escape"}]},
            ).execute()

            # Server type
            answers["type"] = inquirer.select(
                message="Server type:",
                choices=[
                    {"name": "STDIO Server (local command)", "value": "stdio"},
                    {"name": "Remote Server (HTTP/SSE)", "value": "remote"},
                ],
                keybindings={"interrupt": [{"key": "escape"}]},
            ).execute()

            if answers["type"] == "stdio":
                # STDIO Server configuration
                console.print("\n[cyan]STDIO Server Configuration[/]")

                answers["command"] = inquirer.text(
                    message="Command to execute:",
                    validate=lambda text: len(text.strip()) > 0,
                    invalid_message="Command cannot be empty",
                    keybindings={"interrupt": [{"key": "escape"}]},
                ).execute()

                answers["args"] = inquirer.text(
                    message="Arguments (space-separated, quotes supported):",
                    instruction="(Leave empty for no arguments, use quotes for args with spaces)",
                    keybindings={"interrupt": [{"key": "escape"}]},
                ).execute()

                answers["env"] = inquirer.text(
                    message="Environment variables (KEY=value,KEY2=value2):",
                    instruction="(Leave empty for no environment variables)",
                    keybindings={"interrupt": [{"key": "escape"}]},
                ).execute()

            else:  # remote
                # Remote Server configuration
                console.print("\n[cyan]Remote Server Configuration[/]")

                answers["url"] = inquirer.text(
                    message="Server URL:",
                    validate=lambda text: text.strip().startswith(("http://", "https://")) if text.strip() else False,
                    invalid_message="URL must start with http:// or https://",
                    keybindings={"interrupt": [{"key": "escape"}]},
                ).execute()

                answers["headers"] = inquirer.text(
                    message="HTTP headers (KEY=value,KEY2=value2):",
                    instruction="(Leave empty for no custom headers)",
                    keybindings={"interrupt": [{"key": "escape"}]},
                ).execute()

            # Confirmation
            console.print("\n[bold]Summary of new server:[/]")
            console.print(f"Name: [cyan]{answers['name']}[/]")
            console.print(f"Type: [cyan]{answers['type'].upper()}[/]")

            if answers["type"] == "stdio":
                console.print(f"Command: [cyan]{answers['command']}[/]")
                new_args = shlex.split(answers["args"]) if answers["args"] else []
                console.print(f"Arguments: [cyan]{new_args}[/]")

                new_env = {}
                if answers["env"]:
                    for env_pair in answers["env"].split(","):
                        if "=" in env_pair:
                            key, value = env_pair.split("=", 1)
                            new_env[key.strip()] = value.strip()
                console.print(f"Environment: [cyan]{new_env}[/]")

            else:  # remote
                console.print(f"URL: [cyan]{answers['url']}[/]")

                new_headers = {}
                if answers["headers"]:
                    for header_pair in answers["headers"].split(","):
                        if "=" in header_pair:
                            key, value = header_pair.split("=", 1)
                            new_headers[key.strip()] = value.strip()
                console.print(f"Headers: [cyan]{new_headers}[/]")

            confirm = inquirer.confirm(
                message="Create this server?",
                default=True,
                keybindings={"interrupt": [{"key": "escape"}]},
            ).execute()

            if not confirm:
                return {"cancelled": True}

        finally:
            # Restore original argv
            sys.argv = original_argv

        return {
            "cancelled": False,
            "answers": answers,
        }

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Operation cancelled[/]")
        return {"cancelled": True}
    except Exception as e:
        console.print(f"[red]Error running interactive form: {e}[/]")
        return None
