"""
List command for MCP
"""

import click
from rich.console import Console
from rich.table import Table
from rich.markup import escape

from mcp.clients.claude_desktop import ClaudeDesktopManager
from mcp.clients.windsurf import WindsurfManager
from mcp.utils.config import ConfigManager

console = Console()
config_manager = ConfigManager()
claude_manager = ClaudeDesktopManager()
windsurf_manager = WindsurfManager()

@click.command(name="list")
@click.option("--available", is_flag=True, help="List all available MCP servers")
@click.option("--outdated", is_flag=True, help="List installed servers with updates available")
def list(available, outdated):
    """List all installed MCP servers.
    
    Examples:
        mcp list
        mcp list --available
        mcp list --outdated
    """
    if available:
        console.print("[bold green]Available MCP servers:[/]")
        
        # Show available servers that can be installed
        table = Table(show_header=True, header_style="bold")
        table.add_column("Name")
        table.add_column("Description")
        table.add_column("Latest Version")
        
        # Example available servers (in a full implementation, this would come from a repository)
        available_servers = [
            ("filesystem", "Access local files and directories", "1.0.0"),
            ("browser", "Access web content through Claude", "0.9.2"),
            ("code-interpreter", "Execute and interpret code", "0.7.1"),
            ("shell", "Run shell commands from Claude", "0.8.5")
        ]
        
        for name, desc, version in available_servers:
            table.add_row(name, desc, version)
        
        console.print(table)
        
    elif outdated:
        console.print("[bold yellow]Checking for outdated MCP servers...[/]")
        
        # Get the active client and its corresponding manager
        active_client = config_manager.get_active_client()
        
        # Select appropriate client manager based on active client
        if active_client == "claude-desktop":
            client_manager = claude_manager
            client_name = "Claude Desktop"
        elif active_client == "windsurf":
            client_manager = windsurf_manager
            client_name = "Windsurf"
        else:
            console.print(f"[bold red]Error:[/] Unsupported active client: {active_client}")
            console.print("Please switch to a supported client using 'mcp client <client-name>'")
            return
        
        # Get servers from active client
        servers = client_manager.get_servers()
        
        if not servers:
            console.print(f"[yellow]No MCP servers found in {client_name}.[/]")
            return
        
        # In a full implementation, this would check the repository for newer versions
        # For now, just show installed servers with mock version information
        
        # Mock repository versions (would be fetched from a real repository in production)
        repo_versions = {
            "filesystem": "1.1.0",  # Newer than installed
            "browser": "0.9.2",     # Same as installed
            "shell": "0.8.5",       # Same as installed
        }
        
        # Check for outdated servers
        outdated_servers = []
        for server_name in servers:
            # Mock: filesystem has newer version available
            if server_name == "filesystem":
                outdated_servers.append({
                    "name": server_name,
                    "installed": "1.0.0",
                    "latest": repo_versions.get(server_name, "unknown")
                })
        
        if outdated_servers:
            table = Table(show_header=True, header_style="bold")
            table.add_column("Name")
            table.add_column("Installed Version")
            table.add_column("Latest Version")
            table.add_column("Status")
            
            for server in outdated_servers:
                table.add_row(
                    server["name"],
                    server["installed"],
                    server["latest"],
                    "[yellow]Update available[/]"
                )
            
            console.print(table)
        else:
            console.print("[green]All MCP servers are up to date.[/]")
    
    else:
        # Get the active client and its corresponding manager
        active_client = config_manager.get_active_client()
        
        # Select appropriate client manager based on active client
        if active_client == "claude-desktop":
            client_manager = claude_manager
            client_name = "Claude Desktop"
        elif active_client == "windsurf":
            client_manager = windsurf_manager
            client_name = "Windsurf"
        else:
            console.print(f"[bold red]Error:[/] Unsupported active client: {active_client}")
            console.print("Please switch to a supported client using 'mcp client <client-name>'")
            return
        
        console.print(f"[bold green]MCP servers installed in {client_name}:[/]")
        
        # Get all servers from active client config
        servers = client_manager.get_servers()
        
        if not servers:
            console.print(f"[yellow]No MCP servers found in {client_name}.[/]")
            console.print("Use 'mcp install <server>' to install a server.")
            return
        
        # Count the configured servers
        server_count = len(servers)
        console.print(f"[bold]Configured servers:[/] {server_count}\n")
        
        # Display detailed information for each server
        for server_name, server_info in servers.items():
            # Server name and command
            console.print(f"[bold cyan]{server_name}[/]")
            command = server_info.get("command", "N/A")
            console.print(f"  Command: [green]{command}[/]")
            
            # Display arguments
            args = server_info.get("args", [])
            if args:
                console.print("  Arguments:")
                for i, arg in enumerate(args):
                    console.print(f"    {i}: [yellow]{escape(arg)}[/]")
                
                # Get package name (usually the second argument)
                if len(args) > 1:
                    console.print(f"  Package: [magenta]{args[1]}[/]")
            
            # Display environment variables
            env_vars = server_info.get("env", {})
            if env_vars:
                console.print("  Environment Variables:")
                for key, value in env_vars.items():
                    console.print(f"    [bold blue]{key}[/] = [green]\"{value}\"[/]")
            else:
                console.print("  Environment Variables: [italic]None[/]")
            
            # Add a separator line between servers
            console.print("  " + "-" * 50)
