"""
Share command for MCPM - Share a single MCP server through a tunnel
"""

import secrets
import signal
import subprocess
import sys
import time

import click
from rich.console import Console

from mcpm.router.share import Tunnel
from mcpm.utils.config import DEFAULT_SHARE_ADDRESS

console = Console()


@click.command()
@click.argument("command", type=str)
@click.option("--port", type=int, default=8080, help="Port the SSE server listens on")
@click.option("--address", type=str, default=None, help="Remote address for tunnel")
@click.option("--http", is_flag=True, default=False, help="Use HTTP instead of HTTPS")
@click.help_option("-h", "--help")
def share(command, port, address, http):
    """Share an MCP SSE server command through a tunnel.

    COMMAND is the shell command to run the MCP server.

    Example:

        mcpm share "python server.py"
        mcpm share "uvicorn myserver:app" --port 5000
    """
    # Default to standard share address if not specified
    if not address:
        address = DEFAULT_SHARE_ADDRESS
        console.print(f"[cyan]Using default share address: {address}[/]")

    # Split remote host and port
    remote_host, remote_port = address.split(":")
    remote_port = int(remote_port)

    # Start the server process
    console.print(f"[cyan]Starting server with command: [bold]{command}[/bold][/]")
    server_process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1
    )

    # Wait a moment for the server to start
    console.print(f"[cyan]Waiting for server to start on port {port}...[/]")
    time.sleep(2)  # Allow the server to start

    # Check if the process is still running
    if server_process.poll() is not None:
        console.print("[bold red]Error:[/] Server process terminated unexpectedly")
        # Print stderr output to help with debugging
        stderr_output = server_process.stderr.read()
        console.print(f"[red]Server error output:[/]\n{stderr_output}")
        return

    # Create and start the tunnel
    try:
        console.print(f"[cyan]Creating tunnel from localhost:{port} to {remote_host}:{remote_port}...[/]")
        # Generate a random token for security
        share_token = secrets.token_urlsafe(32)
        tunnel = Tunnel(
            remote_host=remote_host,
            remote_port=remote_port,
            local_host="localhost",
            local_port=port,
            share_token=share_token,
            http=http,
            share_server_tls_certificate=None,
        )

        share_url = tunnel.start_tunnel()

        # Display the share URL
        console.print(f"[bold green]Server is now shared at: [/][bold cyan]{share_url}[/]")
        console.print("[yellow]Press Ctrl+C to stop sharing and terminate the server[/]")

        # Handle cleanup on termination signals
        def signal_handler(sig, frame):
            console.print("\n[yellow]Terminating server and tunnel...[/]")
            tunnel.kill()
            if server_process.poll() is None:
                server_process.terminate()
                server_process.wait(timeout=5)
            sys.exit(0)

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Keep the main process running and display server output
        while True:
            if server_process.poll() is not None:
                console.print("[bold red]Server process terminated unexpectedly[/]")
                tunnel.kill()
                break

            # Print server output
            if server_process.stdout:
                line = server_process.stdout.readline()
                if line:
                    print(line, end="")

            # Also check stderr
            if server_process.stderr:
                line = server_process.stderr.readline()
                if line:
                    print(line, end="")

            time.sleep(0.1)

    except Exception as e:
        console.print(f"[bold red]Error:[/] {str(e)}")
        # Clean up
        if server_process.poll() is None:
            server_process.terminate()
            server_process.wait(timeout=5)
        if "tunnel" in locals():
            tunnel.kill()
