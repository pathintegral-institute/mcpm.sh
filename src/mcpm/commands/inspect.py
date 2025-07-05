"""Inspect command for MCPM - Launch MCP Inspector for specific servers"""

import shlex
import subprocess
import sys

from rich.console import Console
from rich.panel import Panel

from mcpm.global_config import GlobalConfigManager
from mcpm.utils.platform import NPX_CMD
from mcpm.utils.rich_click_config import click

console = Console()
global_config_manager = GlobalConfigManager()


def find_installed_server(server_name):
    """Find an installed server by name in global configuration."""
    server_config = global_config_manager.get_server(server_name)
    if server_config:
        return server_config, "global"
    return None, None


def build_inspector_command(server_config, server_name):
    """Build the inspector command from server configuration."""
    if not server_config:
        return None

    # Use mcpm run to execute the server - this handles all the configuration properly
    mcpm_run_cmd = f"mcpm run {shlex.quote(server_name)}"

    # Build full inspector command that uses mcpm run
    inspector_cmd = f"{NPX_CMD} @modelcontextprotocol/inspector {mcpm_run_cmd}"

    return inspector_cmd


def launch_raw_inspector():
    """Launch raw MCP Inspector without a specified server."""
    # Show information panel with options
    panel_content = """[bold]MCP Inspector without a specific server[/]

This will launch the raw MCP Inspector where you can manually configure
the connection to any MCP server.

[bold]To inspect MCPM-managed servers instead:[/]
  • Run [cyan]mcpm ls[/] to see available servers
  • Run [cyan]mcpm inspect <server-name>[/] to inspect a specific server

Examples:
  [cyan]mcpm inspect filesystem[/]     # Inspect filesystem server
  [cyan]mcpm inspect time[/]           # Inspect time server

[bold yellow]Continue with raw inspector?[/]"""

    panel = Panel(panel_content, title="🔍 MCP Inspector", border_style="yellow", padding=(1, 2))
    console.print(panel)

    # Prompt for confirmation
    try:
        confirm = click.confirm("Launch raw MCP Inspector", default=True)
        if not confirm:
            console.print("[yellow]Cancelled.[/]")
            sys.exit(0)
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Cancelled.[/]")
        sys.exit(0)

    # Launch raw inspector
    raw_inspector_cmd = f"{NPX_CMD} @modelcontextprotocol/inspector"

    console.print("\n[bold]Launching raw MCP Inspector...[/]")
    console.print("The Inspector UI will open in your web browser.")
    console.print("[yellow]Press Ctrl+C to stop the Inspector.[/]")

    try:
        console.print(f"[dim]Executing: {raw_inspector_cmd}[/]")
        cmd_parts = shlex.split(raw_inspector_cmd)
        returncode = subprocess.call(cmd_parts)

        if returncode == 0:
            console.print("[bold green]Inspector process completed successfully.[/]")
        elif returncode in (130, -2):
            console.print("[bold yellow]Inspector process was terminated.[/]")
        else:
            console.print(f"[bold red]Inspector process exited with code {returncode}[/]")

        sys.exit(returncode)

    except KeyboardInterrupt:
        console.print("\n[bold yellow]Inspector process terminated by keyboard interrupt.[/]")
        sys.exit(130)
    except FileNotFoundError:
        console.print("[bold red]Error:[/] Could not find npx. Please make sure Node.js is installed.")
        console.print("Install Node.js from https://nodejs.org/")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error launching Inspector:[/] {str(e)}")
        sys.exit(1)


@click.command()
@click.argument("server_name", required=False)
@click.help_option("-h", "--help")
def inspect(server_name):
    """Launch MCP Inspector to test and debug a server from global configuration.

    If SERVER_NAME is provided, finds the specified server in the global configuration
    and launches the MCP Inspector with the correct configuration to connect to and test the server.

    If no SERVER_NAME is provided, launches the raw MCP Inspector for manual configuration.

    Examples:
        mcpm inspect                     # Launch raw inspector (manual setup)
        mcpm inspect mcp-server-browse   # Inspect the browse server
        mcpm inspect filesystem          # Inspect filesystem server
        mcpm inspect time                # Inspect the time server
    """
    # Handle case where no server name is provided
    if not server_name or not server_name.strip():
        return launch_raw_inspector()

    server_name = server_name.strip()

    # Show header
    console.print(
        Panel.fit(f"[bold green]MCPM Inspector[/]\nInspecting server: [cyan]{server_name}[/]", border_style="cyan")
    )

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

    # Build inspector command
    inspector_cmd = build_inspector_command(server_config, server_name)

    if not inspector_cmd:
        console.print(f"[red]Error: Invalid server configuration for '{server_name}'[/]")
        sys.exit(1)

    # Show server info
    console.print(f"[dim]Found server in: {location} configuration[/]")
    console.print(f"[dim]Server will be launched via: mcpm run {server_name}[/]")

    # No confirmation needed - inspect is a low-risk debugging operation
    console.print(f"\n[bold]Starting Inspector for server '[cyan]{server_name}[/]'[/]")
    console.print("The Inspector UI will open in your web browser.")

    try:
        console.print("[cyan]Starting MCPM Inspector...[/]")
        console.print("The Inspector UI will open in your web browser.")
        console.print("[yellow]Press Ctrl+C to stop the Inspector.[/]")

        # Split the command into components for subprocess
        cmd_parts = shlex.split(inspector_cmd)

        try:
            console.print(f"[dim]Executing: {inspector_cmd}[/]")
            console.print("[bold green]Starting MCPM Inspector...[/]")
            console.print("[cyan]Press Ctrl+C to exit[/]")
            sys.stdout.flush()

            # Execute the command with direct terminal access
            # No need to handle env vars - mcpm run will handle them
            returncode = subprocess.call(cmd_parts)

        except KeyboardInterrupt:
            console.print("\n[bold yellow]Inspector process terminated by keyboard interrupt.[/]")
            returncode = 130

        # Check exit code
        if returncode == 0:
            console.print("[bold green]Inspector process completed successfully.[/]")
        elif returncode in (130, -2):
            console.print("[bold yellow]Inspector process was terminated.[/]")
        else:
            console.print(f"[bold red]Inspector process exited with code {returncode}[/]")

        sys.exit(returncode)

    except FileNotFoundError:
        console.print("[bold red]Error:[/] Could not find npx. Please make sure Node.js is installed.")
        console.print("Install Node.js from https://nodejs.org/")
        sys.exit(1)
    except PermissionError:
        console.print("[bold red]Error:[/] Permission denied while trying to execute the command.")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error launching Inspector:[/] {str(e)}")
        sys.exit(1)
