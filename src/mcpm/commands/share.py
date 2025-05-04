"""
Share command for MCPM - Share a single MCP server through a tunnel
"""

import secrets
import shlex
import shutil
import signal
import subprocess
import sys
import time
from typing import Optional, Tuple

import click
from rich.console import Console

from mcpm.router.share import Tunnel
from mcpm.utils.config import DEFAULT_SHARE_ADDRESS

console = Console()


def find_mcp_proxy() -> Optional[str]:
    """Find the mcp-proxy executable in PATH."""
    return shutil.which("mcp-proxy")


def start_mcp_proxy(command: str, port: Optional[int] = None) -> Tuple[subprocess.Popen, int]:
    """
    Start mcp-proxy to convert a stdio MCP server to an SSE server.

    Args:
        command: The command to run the stdio MCP server
        port: The port for the SSE server (random if None)

    Returns:
        A tuple of (process, port)
    """
    mcp_proxy_path = find_mcp_proxy()
    if not mcp_proxy_path:
        console.print("[bold red]Error:[/] mcp-proxy not found in PATH")
        console.print("Please install mcp-proxy using one of the following methods:")
        console.print("  - pip install mcp-proxy")
        console.print("  - uv tool install mcp-proxy")
        console.print("  - npx -y @smithery/cli install mcp-proxy")
        sys.exit(1)

    # Build the mcp-proxy command
    cmd_parts = [mcp_proxy_path]

    # Add port if specified
    if port:
        cmd_parts.extend(["--sse-port", str(port)])

    # Add the command to run the stdio server using -- separator
    cmd_parts.append("--")
    cmd_parts.extend(shlex.split(command))

    # Start mcp-proxy as a subprocess
    console.print(f"[cyan]Running command: [bold]{' '.join(cmd_parts)}[/bold][/]")
    process = subprocess.Popen(cmd_parts, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

    # If port is None, we need to parse the output to find the random port
    actual_port = port
    if not actual_port:
        # Wait for mcp-proxy to output the port information
        start_time = time.time()
        port_found = False

        while time.time() - start_time < 15:  # Extended timeout
            if process.stderr:
                line = process.stderr.readline()
                if line:
                    print(line, end="")
                    # Look for different possible port indicators in the output
                    if "Serving on" in line:
                        try:
                            actual_port = int(line.split(":")[-1].strip())
                            port_found = True
                            break
                        except (ValueError, IndexError):
                            pass
                    elif "Uvicorn running on http://" in line:
                        try:
                            url_part = line.split("Uvicorn running on ")[1].split(" ")[0]
                            actual_port = int(url_part.split(":")[-1].strip())
                            port_found = True
                            break
                        except (ValueError, IndexError):
                            pass

            if process.stdout:
                line = process.stdout.readline()
                if line:
                    print(line, end="")
                    # Also check stdout for port information
                    if "Uvicorn running on http://" in line:
                        try:
                            url_part = line.split("Uvicorn running on ")[1].split(" ")[0]
                            actual_port = int(url_part.split(":")[-1].strip())
                            port_found = True
                            break
                        except (ValueError, IndexError):
                            pass

            if process.poll() is not None:
                # Process terminated prematurely
                stderr_output = process.stderr.read() if process.stderr else ""
                console.print("[bold red]Error:[/] mcp-proxy terminated unexpectedly")
                console.print(f"[red]Error output:[/]\n{stderr_output}")
                sys.exit(1)

            time.sleep(0.1)

        if not port_found and not actual_port:
            console.print("[bold red]Error:[/] Could not determine the port mcp-proxy is running on")
            process.terminate()
            sys.exit(1)

    if not actual_port:
        console.print("[bold red]Error:[/] Could not determine the port mcp-proxy is running on")
        process.terminate()
        sys.exit(1)

    return process, actual_port


@click.command()
@click.argument("command", type=str)
@click.option("--port", type=int, default=None, help="Port for the SSE server (random if not specified)")
@click.option("--address", type=str, default=None, help="Remote address for tunnel, use share.mcpm.sh if not specified")
@click.option(
    "--http", is_flag=True, default=False, help="Use HTTP instead of HTTPS. NOT recommended to use on public networks."
)
@click.help_option("-h", "--help")
def share(command, port, address, http):
    """Share an MCP server through a tunnel.

    This command uses mcp-proxy to expose a stdio MCP server as an SSE server,
    then creates a tunnel to make it accessible remotely.

    COMMAND is the shell command to run the MCP server.

    Examples:

    \b
        mcpm share "python stdio_server.py"
        mcpm share "npx mcp-server" --port 5000
        mcpm share "uv run my-mcp-server" --address myserver.com:7000
    """
    # Default to standard share address if not specified
    if not address:
        address = DEFAULT_SHARE_ADDRESS
        console.print(f"[cyan]Using default share address: {address}[/]")

    # Split remote host and port
    remote_host, remote_port = address.split(":")
    remote_port = int(remote_port)

    # Start mcp-proxy to convert stdio to SSE
    console.print(f"[cyan]Starting mcp-proxy with command: [bold]{command}[/bold][/]")
    try:
        server_process, actual_port = start_mcp_proxy(command, port)
        console.print(f"[cyan]mcp-proxy SSE server running on port [bold]{actual_port}[/bold][/]")

        # Create and start the tunnel
        console.print(f"[cyan]Creating tunnel from localhost:{actual_port} to {remote_host}:{remote_port}...[/]")
        # Generate a random token for security
        share_token = secrets.token_urlsafe(32)
        tunnel = Tunnel(
            remote_host=remote_host,
            remote_port=remote_port,
            local_host="localhost",
            local_port=actual_port,
            share_token=share_token,
            http=http,
            share_server_tls_certificate=None,
        )

        share_url = tunnel.start_tunnel()

        # Display the share URL - append /sse for mcp-proxy's SSE endpoint
        sse_url = f"{share_url}/sse"
        console.print(f"[bold green]Server is now shared at: [/][bold cyan]{sse_url}[/]")
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
        if "server_process" in locals() and server_process.poll() is None:
            server_process.terminate()
            server_process.wait(timeout=5)
        if "tunnel" in locals():
            tunnel.kill()
