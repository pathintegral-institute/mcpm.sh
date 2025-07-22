"""Config command for MCPM - Manage MCPM configuration"""

import os
import sys

from rich.console import Console
from rich.prompt import Prompt

from mcpm.utils.config import NODE_EXECUTABLES, ConfigManager
from mcpm.utils.non_interactive import is_non_interactive, should_force_operation
from mcpm.utils.repository import RepositoryManager
from mcpm.utils.rich_click_config import click

console = Console()
repo_manager = RepositoryManager()


@click.group()
@click.help_option("-h", "--help")
def config():
    """Manage MCPM configuration.

    Commands for managing MCPM configuration and cache.
    """
    pass


@config.command()
@click.option("--key", help="Configuration key to set")
@click.option("--value", help="Configuration value to set")
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
@click.help_option("-h", "--help")
def set(key, value, force):
    """Set MCPM configuration.

    Interactive by default, or use CLI parameters for automation.
    Use --key and --value to set configuration non-interactively.

    Examples:

    \b
        mcpm config set                                    # Interactive mode
        mcpm config set --key node_executable --value npx # Non-interactive mode
    """
    config_manager = ConfigManager()

    # Check if we have CLI parameters for non-interactive mode
    has_cli_params = key is not None and value is not None
    force_non_interactive = is_non_interactive() or should_force_operation() or force

    if has_cli_params or force_non_interactive:
        exit_code = _set_config_non_interactive(
            config_manager=config_manager,
            key=key,
            value=value,
            force=force
        )
        sys.exit(exit_code)

    # Interactive mode
    set_key = Prompt.ask("Configuration key to set", choices=["node_executable"], default="node_executable")

    if set_key == "node_executable":
        node_executable = Prompt.ask(
            "Select default node executable, it will be automatically applied when adding npx server with mcpm add",
            choices=NODE_EXECUTABLES,
        )
        config_manager.set_config(set_key, node_executable)
        console.print(f"[green]Default node executable set to:[/] {node_executable}")
    else:
        console.print(f"[red]Error: Unknown configuration key '{set_key}'[/]")


def _set_config_non_interactive(config_manager, key=None, value=None, force=False):
    """Set configuration non-interactively."""
    try:
        # Define supported configuration keys and their valid values
        SUPPORTED_KEYS = {
            "node_executable": {
                "valid_values": NODE_EXECUTABLES,
                "description": "Default node executable for npx servers"
            }
        }

        # Validate that both key and value are provided in non-interactive mode
        if not key or not value:
            console.print("[red]Error: Both --key and --value are required in non-interactive mode[/]")
            console.print("[dim]Use 'mcpm config set' for interactive mode[/]")
            return 1

        # Validate the configuration key
        if key not in SUPPORTED_KEYS:
            console.print(f"[red]Error: Unknown configuration key '{key}'[/]")
            console.print("[yellow]Supported keys:[/]")
            for supported_key, info in SUPPORTED_KEYS.items():
                console.print(f"  • [cyan]{supported_key}[/] - {info['description']}")
            return 1

        # Validate the value for the specific key
        key_info = SUPPORTED_KEYS[key]
        if "valid_values" in key_info and value not in key_info["valid_values"]:
            console.print(f"[red]Error: Invalid value '{value}' for key '{key}'[/]")
            console.print(f"[yellow]Valid values for '{key}':[/]")
            for valid_value in key_info["valid_values"]:
                console.print(f"  • [cyan]{valid_value}[/]")
            return 1

        # Display what will be set
        console.print("[bold green]Setting configuration:[/]")
        console.print(f"Key: [cyan]{key}[/]")
        console.print(f"Value: [cyan]{value}[/]")

        # Set the configuration
        success = config_manager.set_config(key, value)
        if success:
            console.print(f"[green]✅ Configuration '{key}' set to '{value}'[/]")
            return 0
        else:
            console.print(f"[red]Error: Failed to set configuration '{key}'[/]")
            return 1

    except Exception as e:
        console.print(f"[red]Error setting configuration: {e}[/]")
        return 1


@config.command()
@click.help_option("-h", "--help")
def ls():
    """List all MCPM configuration settings.

    Example:

    \b
        mcpm config ls
    """
    config_manager = ConfigManager()
    current_config = config_manager.get_config()

    if not current_config:
        console.print("[yellow]No configuration settings found.[/]")
        return

    console.print("[bold green]Current configuration:[/]")
    for key, value in current_config.items():
        console.print(f"  [cyan]{key}:[/] {value}")


@config.command()
@click.argument("name", required=True)
@click.help_option("-h", "--help")
def unset(name):
    """Remove a configuration setting.

    Example:

    \b
        mcpm config unset node_executable
    """
    config_manager = ConfigManager()
    current_config = config_manager.get_config()

    if name not in current_config:
        console.print(f"[red]Configuration '{name}' is not set.[/]")
        return

    # Remove the configuration by setting it to None
    config_manager.set_config(name, None)
    console.print(f"[green]Configuration '{name}' has been removed.[/]")


@config.command()
@click.help_option("-h", "--help")
def clear_cache():
    """Clear the local repository cache.

    Removes the cached server information, forcing a fresh download on next search.

    Examples:
        mcpm config clear-cache    # Clear the local repository cache
    """
    try:
        # Check if cache file exists
        if os.path.exists(repo_manager.cache_file):
            # Remove the cache file
            os.remove(repo_manager.cache_file)
            console.print(f"[green]Successfully cleared repository cache at:[/] {repo_manager.cache_file}")
            console.print("Cache will be rebuilt on next search.")
        else:
            console.print(f"[yellow]Cache file not found at:[/] {repo_manager.cache_file}")
            console.print("No action needed.")
    except Exception as e:
        console.print(f"[bold red]Error clearing cache:[/] {str(e)}")
