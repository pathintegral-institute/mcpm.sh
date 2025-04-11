"""Config command for MCPM - Manage MCPM configuration"""

import os

import click
from rich.console import Console

from mcpm.utils.repository import RepositoryManager

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
