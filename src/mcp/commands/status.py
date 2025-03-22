"""
Status command for MCP
"""

import os
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markup import escape

from mcp.clients.claude_desktop import ClaudeDesktopManager

console = Console()
claude_manager = ClaudeDesktopManager()

@click.command()
@click.argument("server_name", required=False)
def status(server_name):
    """Show status of MCP servers in Claude Desktop.
    
    Examples:
        mcp status
        mcp status filesystem
    """
    # First, check if Claude Desktop is installed
    if not claude_manager.is_claude_desktop_installed():
        console.print("[bold red]Error:[/] Claude Desktop installation not detected.")
        console.print("Please download and install Claude Desktop from https://claude.ai/download")
        return
    
    # Check if Claude Desktop config file exists
    if not os.path.exists(claude_manager.config_path):
        console.print(f"[yellow]Claude Desktop config file not found at:[/] {claude_manager.config_path}")
        console.print("You may need to create it by opening Claude Desktop settings > Developer > Edit Config")
        return
    
    if server_name:
        # Show status for a specific server
        server_config = claude_manager.get_server(server_name)
        if not server_config:
            console.print(f"[bold red]Error:[/] Server '{server_name}' not found in Claude Desktop.")
            return
        
        console.print(f"[bold green]Status for MCP server:[/] {server_name}")
        
        # Display detailed info for this server
        command = server_config.get("command", "N/A")
        args = server_config.get("args", [])
        
        # Build a rich panel with server details
        content = f"[bold]Server:[/] {server_name}\n"
        content += f"[bold]Command:[/] {command}\n"
        content += "[bold]Arguments:[/]\n"
        for i, arg in enumerate(args):
            content += f"  {i}: {escape(arg)}\n"
        
        # Check if the server process might be running (mock implementation)
        running_status = "[yellow]Unknown[/]"
        if command == "npx" and len(args) > 1:
            # Check if npx processes are running with this package
            package_name = args[1] if len(args) > 1 else ""
            if _is_server_running(package_name):
                running_status = "[green]Running[/]"
            else:
                running_status = "[red]Not running[/]"
        
        content += f"\n[bold]Status:[/] {running_status}"
        
        panel = Panel(content, title=f"MCP Server: {server_name}", expand=False)
        console.print(panel)
        
        # Show information about Claude Desktop integration
        console.print("\n[bold]Claude Desktop Integration:[/]")
        console.print("This server is configured in Claude Desktop and will be started when Claude Desktop launches.")
        console.print("You may need to restart Claude Desktop for configuration changes to take effect.")
        
    else:
        # Show status for all servers
        console.print("[bold green]Status of MCP servers in Claude Desktop:[/]")
        
        # Get all servers from Claude Desktop config
        claude_servers = claude_manager.get_servers()
        
        if not claude_servers:
            console.print("[yellow]No MCP servers found in Claude Desktop configuration.[/]")
            console.print("Use 'mcp install <server>' to install a server.")
            return
            
        # Display status for all servers
        table = Table(show_header=True, header_style="bold")
        table.add_column("Server")
        table.add_column("Package")
        table.add_column("Status")
        
        for server_name, server_config in claude_servers.items():
            command = server_config.get("command", "N/A")
            args = server_config.get("args", [])
            
            # Get package name
            package = args[1] if len(args) > 1 else "N/A"
            
            # Get runtime status (mock implementation)
            status = "[yellow]Unknown[/]"
            if command == "npx" and len(args) > 1:
                package_name = args[1]
                if _is_server_running(package_name):
                    status = "[green]Running[/]"
                else:
                    status = "[red]Not running[/]"
            
            table.add_row(
                server_name,
                package,
                status
            )
        
        console.print(table)
        console.print("\n[italic yellow]Note: Full status checking functionality coming soon![/]")
        console.print("[italic]Restart Claude Desktop for configuration changes to take effect.[/]")


def _is_server_running(package_name):
    """Check if a server process is running (mock implementation).
    
    Args:
        package_name: The package name to check for
        
    Returns:
        bool: True if running, False otherwise
    """
    # This is a placeholder implementation
    # Full process checking functionality will be implemented in a future release
    # Currently returns False for all servers
    return False
