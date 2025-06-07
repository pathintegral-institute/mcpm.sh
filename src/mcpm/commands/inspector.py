"""
MCPM Inspector command for examining MCP servers through a user interface
"""

import os
import shlex
import subprocess
import sys

import click
from rich.console import Console
from rich.panel import Panel

from mcpm.utils.platform import NPX_CMD

console = Console()

# Define context settings to handle help flag properly
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


@click.command(context_settings=CONTEXT_SETTINGS)
@click.argument("args", nargs=-1)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.help_option("-h", "--help")
def inspector(args, yes):
    """Launch the MCPM Inspector UI to examine servers.

    EXAMPLES:

    Launch the Inspector UI with no arguments:
        mcpm inspector

    Launch the Inspector with custom arguments:
        mcpm inspector npx my-server --port 3000

    Use with NPM packages:
        mcpm inspector npx server-postgres

    Use with Python packages:
        mcpm inspector uvx mcp-server-git
    """
    # Show header
    console.print(
        Panel.fit("[bold green]MCPM Inspector[/]\nModel Context Protocol Inspection Tool", border_style="cyan")
    )

    try:
        # Construct command from args
        if args:
            # Pass all arguments directly to the inspector
            arg_string = " ".join(args)
            cmd = f"{NPX_CMD} @modelcontextprotocol/inspector {arg_string}"
            console.print(f"[bold]Running MCPM Inspector with arguments:[/] {arg_string}")
        else:
            # No arguments provided, prompt for confirmation
            if not yes:
                click.echo("\nStarting MCPM Inspector with no arguments.")
                click.echo("This will launch the Inspector UI without a target server.")
                if not click.confirm("Continue?", default=True):
                    console.print("[yellow]Inspector cancelled.[/]")
                    return

            cmd = f"{NPX_CMD} @modelcontextprotocol/inspector"

        console.print("[cyan]Starting MCPM Inspector...[/]")
        console.print("The Inspector UI will open in your web browser.")
        console.print("[yellow]Press Ctrl+C to stop the Inspector.[/]")

        # Split the command into components for subprocess, properly handling quoted arguments
        cmd_parts = shlex.split(cmd)

        try:
            # Execute the command
            console.print(f"[dim]Executing: {cmd}[/]")

            # Create environment with NODE_PATH if needed
            env = os.environ.copy()

            try:
                # Use subprocess.call for direct terminal I/O
                # This is the simplest way to execute a command with inherited stdio
                console.print("[bold green]Starting MCPM Inspector...[/]")
                console.print("[cyan]Press Ctrl+C to exit[/]")
                sys.stdout.flush()

                # Execute the command with direct terminal access
                # The Python process will wait here until the command completes
                returncode = subprocess.call(cmd_parts, env=env)

            except KeyboardInterrupt:
                # When using subprocess.call, the KeyboardInterrupt is automatically
                # forwarded to the child process, so we just need to acknowledge it
                console.print("\n[bold yellow]Inspector process terminated by keyboard interrupt.[/]")
                returncode = 130  # Standard exit code for SIGINT

            # Check exit code
            if returncode == 0:
                console.print("[bold green]Inspector process completed successfully.[/]")
            elif returncode in (130, -2):  # Exit codes for keyboard interrupt
                console.print("[bold yellow]Inspector process was terminated.[/]")
            else:
                console.print(f"[bold red]Inspector process exited with code {returncode}[/]")

        except FileNotFoundError:
            console.print("[bold red]Error:[/] Could not find npx. Please make sure Node.js is installed.")
            console.print("Install Node.js from https://nodejs.org/")
        except PermissionError:
            console.print("[bold red]Error:[/] Permission denied while trying to execute the command.")

    except Exception as e:
        console.print(f"[bold red]Error launching Inspector:[/] {str(e)}")


def show_inspector_help():
    """Display detailed help for the inspector."""
    console.print(
        Panel.fit(
            "[bold]MCPM Inspector[/]\n\n"
            "The Inspector is a web UI tool that allows you to:\n"
            "- View server connections\n"
            "- Explore resources provided by the server\n"
            "- Test prompts with custom arguments\n"
            "- Execute tools with custom inputs\n"
            "- View server logs and notifications",
            title="MCPM Inspector Help",
            border_style="cyan",
        )
    )

    console.print("\n[bold]Documentation:[/] https://modelcontextprotocol.io/docs/tools/inspector")
    console.print("[bold]Usage examples:[/]\n")
    console.print("  [cyan]mcpm inspector filesystem[/]")
    console.print("    Launch Inspector for an installed server")
    console.print('\n  [cyan]mcpm inspector --package server-postgres --package-args "postgres://127.0.0.1/testdb"[/]')
    console.print("    Inspect an NPM package with arguments")
    console.print("\n  [cyan]mcpm inspector --python --package mcp-server-git[/]")
    console.print("    Inspect a PyPI package")
