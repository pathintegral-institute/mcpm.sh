"""
Install command for MCP
"""

import os
import json
import subprocess
from datetime import datetime

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.panel import Panel

from mcp.utils.repository import RepositoryManager
from mcp.utils.config import ConfigManager
from mcp.utils.client_detector import detect_installed_clients

console = Console()
repo_manager = RepositoryManager()
config_manager = ConfigManager()

@click.command()
@click.argument("server_name")
@click.option("--force", is_flag=True, help="Force reinstall if server is already installed")
def install(server_name, force=False):
    """Install an MCP server.
    
    Examples:
        mcp install time
        mcp install github
        mcp install everything --force
    """
    # Check if already installed
    existing_server = config_manager.get_server_info(server_name)
    if existing_server and not force:
        console.print(f"[yellow]Server '{server_name}' is already installed (v{existing_server.get('version', 'unknown')}).[/]")
        console.print("Use 'mcp install --force' to reinstall or 'mcp update' to update it to a newer version.")
        return
    
    # Get server metadata from repository
    server_metadata = repo_manager.get_server_metadata(server_name)
    if not server_metadata:
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in registry.")
        console.print(f"Available servers: {', '.join(repo_manager._fetch_servers().keys())}")
        return
    
    # Display server information
    display_name = server_metadata.get("display_name", server_name)
    description = server_metadata.get("description", "No description available")
    available_version = server_metadata.get("version")
    author_info = server_metadata.get("author", {})
    author_name = author_info.get("name", "Unknown")
    license_info = server_metadata.get("license", "Unknown")
    
    # Use the available version
    version = available_version
    
    # Display server information
    console.print(Panel(
        f"[bold]{display_name}[/] [dim]v{version}[/]\n" +
        f"[italic]{description}[/]\n\n" +
        f"Author: {author_name}\n" +
        f"License: {license_info}",
        title="Server Information",
        border_style="green",
    ))
    
    # Check for API key requirements
    requirements = server_metadata.get("requirements", {})
    needs_api_key = requirements.get("api_key", False)
    auth_type = requirements.get("authentication")
    
    if needs_api_key:
        console.print("[yellow]Note:[/] This server requires an API key or authentication.")
        if auth_type:
            console.print(f"Authentication type: [bold]{auth_type}[/]")
    
    # Installation preparation
    if not force and existing_server:
        if not Confirm.ask(f"Server '{server_name}' is already installed. Do you want to reinstall?"):
            return
    
    # Create server directory
    server_dir = os.path.expanduser(f"~/.config/mcp/servers/{server_name}")
    os.makedirs(server_dir, exist_ok=True)
    
    # Get installation instructions
    installation = server_metadata.get("installation", {})
    install_command = installation.get("command")
    install_args = installation.get("args", [])
    package_name = installation.get("package")
    env_vars = installation.get("env", {})
    
    if not install_command or not install_args:
        console.print(f"[bold red]Error:[/] Invalid installation information for server '{server_name}'.")
        return
    
    # Download and install server
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]{task.description}[/]"),
        console=console
    ) as progress:
        # Download metadata
        progress.add_task("Downloading server metadata...", total=None)
        # Save metadata to server directory
        metadata_path = os.path.join(server_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(server_metadata, f, indent=2)
        
        # Install using the specified command and args
        progress.add_task(f"Installing {server_name} v{version}...", total=None)
        
        try:
            # Prepare environment variables
            env = os.environ.copy()
            
            # Replace variable placeholders with values from environment
            for key, value in env_vars.items():
                if isinstance(value, str) and value.startswith("${"): 
                    env_var_name = value[2:-1]  # Extract variable name from ${NAME}
                    env_value = os.environ.get(env_var_name, "")
                    env[key] = env_value
                    
                    # Warn if variable is not set
                    if not env_value and needs_api_key:
                        console.print(f"[yellow]Warning:[/] Environment variable {env_var_name} is not set")
                else:
                    env[key] = value
            
            # Run installation command
            if install_command:
                full_command = [install_command] + install_args
                console.print(f"Running: [dim]{' '.join(full_command)}[/]")
                
                # Capture installation process output
                result = subprocess.run(
                    full_command,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                if result.returncode != 0:
                    console.print(f"[bold red]Installation failed with error code {result.returncode}[/]")
                    console.print(f"[red]{result.stderr}[/]")
                    return
        except Exception as e:
            console.print(f"[bold red]Error during installation:[/] {str(e)}")
            return
    
    # Create server configuration
    server_info = {
        "name": server_name,
        "display_name": display_name,
        "version": version,
        "description": description,
        "status": "stopped",
        "install_date": datetime.now().strftime("%Y-%m-%d"),
        "path": server_dir,
        "package": package_name
    }
    
    # Register the server in our config
    config_manager.register_server(server_name, server_info)
    
    console.print(f"[bold green]Successfully installed {display_name} v{version}![/]")
    
    # Handle client enablement - automatically enable for active client
    active_client = config_manager.get_active_client()
    installed_clients = detect_installed_clients()
    
    # Enable for active client if installed
    if active_client and installed_clients.get(active_client, False):
        success = config_manager.enable_server_for_client(server_name, active_client)
        if success:
            console.print(f"[green]Enabled {server_name} for active client: {active_client}[/]")
        else:
            console.print(f"[yellow]Failed to enable {server_name} for {active_client}[/]")
    
    # Display usage examples if available
    examples = server_metadata.get("examples", [])
    if examples:
        console.print("\n[bold]Usage Examples:[/]")
        for i, example in enumerate(examples, 1):
            title = example.get("title", f"Example {i}")
            description = example.get("description", "")
            prompt = example.get("prompt", "")
            
            console.print(f"  [cyan]{title}[/]: {description}")
            if prompt:
                console.print(f"  Try: [italic]\"{prompt}\"[/]\n")
