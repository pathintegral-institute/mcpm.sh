"""
Edit command for MCP (formerly config)
"""

import os
import json
import click
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from mcp.clients.claude_desktop import ClaudeDesktopManager
from mcp.clients.windsurf import WindsurfManager
from mcp.utils.config import ConfigManager

console = Console()
config_manager = ConfigManager()
claude_manager = ClaudeDesktopManager()
windsurf_manager = WindsurfManager()

@click.command()
@click.option("--edit", is_flag=True, help="Open the active client's config in default editor")
@click.option("--create", is_flag=True, help="Create a basic config file if it doesn't exist")
def edit(edit, create):
    """View or edit the active MCP client's configuration file.
    
    The edit command operates on the currently active MCP client (set via 'mcp client').
    By default, this is Claude Desktop, but can be changed to other supported clients.
    
    Examples:
        mcp edit           # Show current client's config file location and content
        mcp edit --edit    # Open the config file in your default editor
        mcp edit --create  # Create a basic config file if it doesn't exist
    """
    # Get the active client and its corresponding manager
    active_client = config_manager.get_active_client()
    
    # Select appropriate client manager based on active client
    if active_client == "claude-desktop":
        client_manager = claude_manager
        client_name = "Claude Desktop"
        install_url = "https://claude.ai/download"
        is_installed_method = client_manager.is_claude_desktop_installed
    elif active_client == "windsurf":
        client_manager = windsurf_manager
        client_name = "Windsurf"
        install_url = "https://codeium.com/windsurf/download"
        is_installed_method = client_manager.is_windsurf_installed
    else:
        console.print(f"[bold red]Error:[/] Unsupported active client: {active_client}")
        console.print("Please switch to a supported client using 'mcp client <client-name>'")
        return
    
    # Get the client config file path
    config_path = client_manager.config_path
    
    # Check if the client is installed
    if not is_installed_method():
        console.print(f"[bold red]Error:[/] {client_name} installation not detected.")
        console.print(f"Please download and install {client_name} from {install_url}")
        return
        
    # Check if config file exists
    config_exists = os.path.exists(config_path)
        
    # Display the config file information
    console.print(f"[bold]{client_name} config file:[/] {config_path}")
    console.print(f"[bold]Status:[/] {'[green]Exists[/]' if config_exists else '[yellow]Does not exist[/]'}\n")
    
    # Create config file if requested and it doesn't exist
    if not config_exists and create:
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
                        os.path.expanduser("~/Downloads")
                    ]
                }
            }
        }
        
        # Create the directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Write the template to file
        try:
            with open(config_path, 'w') as f:
                json.dump(basic_config, f, indent=2)
            console.print("[green]Successfully created config file![/]\n")
            config_exists = True
        except Exception as e:
            console.print(f"[bold red]Error creating config file:[/] {str(e)}")
            return
    
    # Show the current configuration if it exists
    if config_exists:
        try:
            with open(config_path, 'r') as f:
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
                        args = server_config.get('args', [])
                        if args:
                            console.print("  Arguments:")
                            for i, arg in enumerate(args):
                                console.print(f"    {i}: [yellow]{arg}[/]")
                        
                        # Display environment variables
                        env_vars = server_config.get('env', {})
                        if env_vars:
                            console.print("  Environment Variables:")
                            for key, value in env_vars.items():
                                console.print(f"    [bold blue]{key}[/] = [green]\"{value}\"[/]")
                        else:
                            console.print("  Environment Variables: [italic]None[/]")
                        
                        # Add a separator line
                        console.print("  " + "-" * 50)
                
            except json.JSONDecodeError:
                console.print("[yellow]Warning: Config file contains invalid JSON[/]")
                
        except Exception as e:
            console.print(f"[bold red]Error reading config file:[/] {str(e)}")
    
    # Prompt to edit if file exists, or if we need to create it
    should_edit = edit
    if not should_edit and config_exists:
        should_edit = Confirm.ask("Would you like to open this file in your default editor?")
    elif not config_exists and not create:
        should_create = Confirm.ask("Config file doesn't exist. Would you like to create it?")
        if should_create:
            # Create a basic config template
            basic_config = {
                "mcpServers": {}
            }
            
            # Create the directory if it doesn't exist
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            
            # Write the template to file
            try:
                with open(config_path, 'w') as f:
                    json.dump(basic_config, f, indent=2)
                console.print("[green]Successfully created config file![/]")
                should_edit = Confirm.ask("Would you like to open it in your default editor?")
                config_exists = True
            except Exception as e:
                console.print(f"[bold red]Error creating config file:[/] {str(e)}")
                return
    
    # Open in default editor if requested
    if should_edit and config_exists:
        try:
            console.print("[bold green]Opening config file in your default editor...[/]")
            
            # Use appropriate command based on platform
            if os.name == 'nt':  # Windows
                os.startfile(config_path)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.run(['open', config_path] if os.uname().sysname == 'Darwin' else ['xdg-open', config_path])
                
            console.print(f"[italic]After editing, {client_name} must be restarted for changes to take effect.[/]")
        except Exception as e:
            console.print(f"[bold red]Error opening editor:[/] {str(e)}")
            console.print(f"You can manually edit the file at: {config_path}")
