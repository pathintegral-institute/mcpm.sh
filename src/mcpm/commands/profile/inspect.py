"""Profile inspect command."""

import shlex
import subprocess
import sys

from rich.console import Console
from rich.panel import Panel

from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.platform import NPX_CMD
from mcpm.utils.rich_click_config import click

console = Console()
profile_config_manager = ProfileConfigManager()


def build_profile_inspector_command(profile_name):
    """Build the inspector command using mcpm profile run."""
    # Use mcpm profile run to start the FastMCP proxy - don't reinvent the wheel!
    mcpm_profile_run_cmd = f"mcpm profile run {shlex.quote(profile_name)}"

    # Build inspector command that uses mcpm profile run
    inspector_cmd = f"{NPX_CMD} @modelcontextprotocol/inspector {mcpm_profile_run_cmd}"
    return inspector_cmd


@click.command(name="inspect")
@click.argument("profile_name")
@click.help_option("-h", "--help")
def inspect_profile(profile_name):
    """Launch MCP Inspector to test and debug all servers in a profile.

    Creates a FastMCP proxy that aggregates all servers in the specified profile
    and launches the MCP Inspector to interact with the combined capabilities.

    Examples:
        mcpm profile inspect web-dev     # Inspect all servers in web-dev profile
        mcpm profile inspect ai          # Inspect all servers in ai profile
        mcpm profile inspect data        # Inspect all servers in data profile
    """
    # Validate profile name
    if not profile_name or not profile_name.strip():
        console.print("[red]Error: Profile name cannot be empty[/]")
        sys.exit(1)

    profile_name = profile_name.strip()

    # Show header
    console.print(
        Panel.fit(
            f"[bold green]MCPM Profile Inspector[/]\\nInspecting profile: [cyan]{profile_name}[/]", border_style="cyan"
        )
    )

    # Check if profile exists
    try:
        profile_servers = profile_config_manager.get_profile(profile_name)
        if profile_servers is None:
            console.print(f"[red]Error: Profile '[bold]{profile_name}[/]' not found[/]")
            console.print()
            console.print("[yellow]Available options:[/]")
            console.print("  • Run 'mcpm profile ls' to see available profiles")
            console.print("  • Run 'mcpm profile create {name}' to create a profile")
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error accessing profile '{profile_name}': {e}[/]")
        sys.exit(1)

    if not profile_servers:
        console.print(f"[yellow]Profile '[bold]{profile_name}[/]' has no servers configured[/]")
        console.print()
        console.print("[dim]Add servers to this profile with:[/]")
        console.print(f"  mcpm profile edit {profile_name}")
        sys.exit(1)

    # Show profile info
    server_count = len(profile_servers)
    console.print(f"[dim]Profile contains {server_count} server(s):[/]")
    for server_config in profile_servers:
        console.print(f"  • [cyan]{server_config.name}[/]")

    console.print(f"\\n[bold]Starting Inspector for profile '[cyan]{profile_name}[/]'[/]")
    console.print("The Inspector will show aggregated capabilities from all servers in the profile.")
    console.print("The Inspector UI will open in your web browser.")

    # Build inspector command using mcpm profile run
    inspector_cmd = build_profile_inspector_command(profile_name)

    try:
        console.print("[cyan]Starting MCPM Profile Inspector...[/]")
        console.print("The Inspector UI will open in your web browser.")
        console.print("[yellow]Press Ctrl+C to stop the Inspector.[/]")

        # Split the command into components for subprocess
        cmd_parts = shlex.split(inspector_cmd)

        try:
            console.print(f"[dim]Executing: {inspector_cmd}[/]")
            console.print("[bold green]Starting MCPM Profile Inspector...[/]")
            console.print("[cyan]Press Ctrl+C to exit[/]")
            sys.stdout.flush()

            # Execute the command with direct terminal access
            returncode = subprocess.call(cmd_parts)

        except KeyboardInterrupt:
            console.print("\\n[bold yellow]Inspector process terminated by keyboard interrupt.[/]")
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
        console.print(f"[bold red]Error launching Profile Inspector:[/] {str(e)}")
        sys.exit(1)
