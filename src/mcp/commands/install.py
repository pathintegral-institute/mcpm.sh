"""
Install command for MCP
"""

import click
from rich.console import Console
from rich.progress import Progress

from mcp.utils.repository import RepositoryManager
from mcp.utils.config import ConfigManager

console = Console()
repo_manager = RepositoryManager()
config_manager = ConfigManager()

@click.command()
@click.argument("server_name")
@click.option("--version", help="Specific version to install")
@click.option("--client", help="Enable for a specific client after installation")
def install(server_name, version, client=None):
    """Install an MCP server.
    
    Examples:
        mcp install filesystem
        mcp install filesystem --version=1.0.0
        mcp install filesystem --client=cursor
    """
    if version:
        console.print(f"[bold green]Installing MCP server:[/] {server_name} (version {version})")
    else:
        console.print(f"[bold green]Installing latest version of MCP server:[/] {server_name}")
    
    # Check if already installed
    if config_manager.get_server_info(server_name):
        console.print(f"[yellow]Server '{server_name}' is already installed.[/]")
        console.print("Use 'mcp update' to update it to a newer version.")
        return
    
    # Search for the server
    server_metadata = repo_manager.get_server_metadata(server_name)
    if not server_metadata:
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in repository.")
        return
    
    # Check version compatibility
    if version and server_metadata["version"] != version:
        console.print(f"[bold red]Error:[/] Version {version} not found. Available version: {server_metadata['version']}")
        return
    
    if not version:
        version = server_metadata["version"]
        console.print(f"Using latest version: {version}")
    
    # Download server (in a real implementation, this would actually download files)
    with Progress() as progress:
        task = progress.add_task(f"Downloading {server_name}...", total=100)
        # Simulate download progress
        for i in range(101):
            progress.update(task, completed=i)
            if i < 100:
                import time
                time.sleep(0.02)
    
    # Register the server in our config
    server_info = {
        "name": server_name,
        "display_name": server_metadata["display_name"],
        "version": version,
        "description": server_metadata["description"],
        "status": "stopped",
        "install_date": "2025-03-22",  # In a real implementation, use current date
        "path": f"~/.config/mcp/servers/{server_name}"
    }
    config_manager.register_server(server_name, server_info)
    
    console.print(f"[bold green]Successfully installed {server_name} v{version}![/]")
    
    # If client option specified, enable for that client
    if client:
        if client not in config_manager.get_config()["clients"]:
            console.print(f"[yellow]Warning: Unknown client '{client}'. Server not enabled for any client.[/]")
        else:
            success = config_manager.enable_server_for_client(server_name, client)
            if success:
                console.print(f"[green]Enabled {server_name} for {client}[/]")
            else:
                console.print(f"[yellow]Failed to enable {server_name} for {client}[/]")
