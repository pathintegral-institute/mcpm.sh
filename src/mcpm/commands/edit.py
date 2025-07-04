"""
Edit command for modifying server configurations
"""

import sys
from typing import Any, Dict, Optional

import click
from InquirerPy import inquirer
from rich.console import Console
from rich.table import Table

from mcpm.core.schema import RemoteServerConfig, STDIOServerConfig
from mcpm.global_config import GlobalConfigManager
from mcpm.utils.display import print_error

console = Console()
global_config_manager = GlobalConfigManager()


@click.command(name="edit", context_settings=dict(help_option_names=["-h", "--help"]))
@click.argument("server_name")
def edit(server_name):
    """Edit a server configuration.

    Opens an interactive form editor that allows you to:
    - Change the server name with real-time validation
    - Modify server-specific properties (command, args, env for STDIO; URL, headers for remote)
    - Step through each field, press Enter to confirm, ESC to cancel
    
    Examples:
    
    \\b
        mcpm edit time                                    # Interactive form
        mcpm edit agentkit                                # Edit agentkit server
        mcpm edit remote-api                              # Edit remote server
    """
    # Get the existing server
    server_config = global_config_manager.get_server(server_name)
    if not server_config:
        print_error(f"Server '{server_name}' not found", "Run 'mcpm ls' to see available servers")
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
        table.add_row("Arguments", ", ".join(server_config.args) if server_config.args else "[dim]None[/]")
        table.add_row("Environment", ", ".join(f"{k}={v}" for k, v in server_config.env.items()) if server_config.env else "[dim]None[/]")
    elif isinstance(server_config, RemoteServerConfig):
        table.add_row("URL", server_config.url)
        table.add_row("Headers", ", ".join(f"{k}={v}" for k, v in server_config.headers.items()) if server_config.headers else "[dim]None[/]")
    
    table.add_row("Profile Tags", ", ".join(server_config.profile_tags) if server_config.profile_tags else "[dim]None[/]")
    
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

                # Arguments as comma-separated string
                current_args = ", ".join(server_config.args) if server_config.args else ""
                answers["args"] = inquirer.text(
                    message="Arguments (comma-separated):",
                    default=current_args,
                    instruction="(Leave empty for no arguments)",
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
                current_headers = ", ".join(f"{k}={v}" for k, v in server_config.headers.items()) if server_config.headers else ""
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
                new_args = [arg.strip() for arg in answers['args'].split(",") if arg.strip()] if answers['args'] else []
                console.print(f"Arguments: [cyan]{server_config.args}[/] → [cyan]{new_args}[/]")
                
                new_env = {}
                if answers['env']:
                    for env_pair in answers['env'].split(","):
                        if "=" in env_pair:
                            key, value = env_pair.split("=", 1)
                            new_env[key.strip()] = value.strip()
                console.print(f"Environment: [cyan]{server_config.env}[/] → [cyan]{new_env}[/]")
                
            elif isinstance(server_config, RemoteServerConfig):
                console.print(f"URL: [cyan]{server_config.url}[/] → [cyan]{answers['url']}[/]")
                
                new_headers = {}
                if answers['headers']:
                    for header_pair in answers['headers'].split(","):
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

        return {
            "cancelled": False,
            "answers": answers,
            "server_type": type(server_config).__name__
        }

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
            server_config.args = [arg.strip() for arg in answers["args"].split(",") if arg.strip()]
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