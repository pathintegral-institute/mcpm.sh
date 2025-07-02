"""Run command for MCPM - Execute servers directly over stdio"""

import os
import subprocess
import sys

import click
from rich.console import Console

from mcpm.global_config import GlobalConfigManager

console = Console()
global_config_manager = GlobalConfigManager()


def find_installed_server(server_name):
    """Find an installed server by name in global configuration."""
    server_config = global_config_manager.get_server(server_name)
    if server_config:
        return server_config, "global"
    return None, None


def execute_server_command(server_config, server_name):
    """Execute a server command with proper environment setup."""
    if not server_config:
        console.print(f"[red]Invalid server configuration for '{server_name}'[/]")
        sys.exit(1)
    
    # Get command and args from the server config
    command = server_config.command
    args = server_config.args or []
    
    if not command:
        console.print(f"[red]Invalid command format for server '{server_name}'[/]")
        sys.exit(1)
    
    # Build the full command list
    full_command = [command] + args
    
    # Set up environment
    env = os.environ.copy()
    
    # Add any environment variables from server config
    if hasattr(server_config, 'env') and server_config.env:
        for key, value in server_config.env.items():
            env[key] = str(value)
    
    # Set working directory if specified
    cwd = getattr(server_config, 'cwd', None)
    if cwd:
        cwd = os.path.expanduser(cwd)
    
    try:
        # Record usage
        from mcpm.commands.usage import record_server_usage
        record_server_usage(server_name, "run")
        
        # Execute the command
        result = subprocess.run(
            full_command,
            env=env,
            cwd=cwd,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
        return result.returncode
        
    except FileNotFoundError:
        console.print(f"[red]Command not found: {full_command[0]}[/]")
        console.print(f"[yellow]Make sure the required runtime is installed[/]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server execution interrupted[/]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error running server '{server_name}': {e}[/]")
        sys.exit(1)


@click.command()
@click.argument("server_name")
@click.help_option("-h", "--help")
def run(server_name):
    """Execute a server from global configuration over stdio.
    
    Runs an installed MCP server directly from the global configuration,
    making it available over stdio for client communication.
    
    Examples:
        mcpm run mcp-server-browse    # Run the browse server
        mcpm run filesystem          # Run filesystem server
        
    Note: This command is typically used in MCP client configurations:
        {"command": ["mcpm", "run", "mcp-server-browse"]}
    """
    # Validate server name
    if not server_name or not server_name.strip():
        console.print("[red]Error: Server name cannot be empty[/]")
        sys.exit(1)
    
    server_name = server_name.strip()
    
    # Find the server configuration
    server_config, location = find_installed_server(server_name)
    
    if not server_config:
        console.print(f"[red]Error: Server '[bold]{server_name}[/]' not found[/]")
        console.print()
        console.print("[yellow]Available options:[/]")
        console.print("  • Run 'mcpm ls' to see installed servers")
        console.print("  • Run 'mcpm search {name}' to find available servers")
        console.print("  • Run 'mcpm install {name}' to install a server")
        sys.exit(1)
    
    # Show debug info in verbose mode or if MCPM_DEBUG is set
    debug = os.getenv("MCPM_DEBUG", "").lower() in ("1", "true", "yes")
    if debug:
        debug_console = Console(file=sys.stderr)
        debug_console.print(f"[dim]Running server '{server_name}' from {location} configuration[/]")
        debug_console.print(f"[dim]Command: {server_config.command} {' '.join(server_config.args or [])}[/]")
    
    # Execute the server
    exit_code = execute_server_command(server_config, server_name)
    sys.exit(exit_code)