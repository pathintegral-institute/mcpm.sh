"""
List command for MCP
"""

import click
from rich.console import Console
from rich.table import Table
from rich.markup import escape

from mcp.clients.claude_desktop import ClaudeDesktopManager

console = Console()
claude_manager = ClaudeDesktopManager()

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
        
        # Get Claude Desktop servers
        claude_servers = claude_manager.get_servers()
        
        if not claude_servers:
            console.print("[yellow]No MCP servers found in Claude Desktop.[/]")
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
        for server_name in claude_servers:
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
        console.print("[bold green]MCP servers installed in Claude Desktop:[/]")
        
        # Get all servers from Claude Desktop config
        claude_servers = claude_manager.get_servers()
        
        if not claude_servers:
            console.print("[yellow]No MCP servers found in Claude Desktop.[/]")
            console.print("Use 'mcp install <server>' to install a server.")
            return
        
        # Count the configured servers
        server_count = len(claude_servers)
        console.print(f"[bold]Configured servers:[/] {server_count}\n")
        
        # Display detailed information for each server
        for server_name, server_info in claude_servers.items():
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
