"""Config command for MCPM - Manage MCPM configuration"""

import os

from rich.console import Console
from rich.prompt import Prompt

from mcpm.utils.config import NODE_EXECUTABLES, ConfigManager
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
@click.help_option("-h", "--help")
def set():
    """Set MCPM configuration.

    Example:

    \b
        mcpm config set
    """
    set_key = Prompt.ask("Configuration key to set", choices=["node_executable"], default="node_executable")
    node_executable = Prompt.ask(
        "Select default node executable, it will be automatically applied when adding npx server with mcpm add",
        choices=NODE_EXECUTABLES,
    )
    config_manager = ConfigManager()
    config_manager.set_config(set_key, node_executable)
    console.print(f"[green]Default node executable set to:[/] {node_executable}")


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
