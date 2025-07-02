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

from mcpm.global_config import GlobalConfigManager
from mcpm.router.share import Tunnel
from mcpm.utils.config import DEFAULT_SHARE_ADDRESS

console = Console()
global_config_manager = GlobalConfigManager()


def find_installed_server(server_name):
    """Find an installed server by name in global configuration."""
    server_config = global_config_manager.get_server(server_name)
    if server_config:
        return server_config, "global"
    return None, None


def build_server_command(server_config, server_name):
    """Build the command to run the server using mcpm run."""
    if not server_config:
        return None
    
    # Use mcpm run to execute the server - this handles all the configuration properly
    return f"mcpm run {shlex.quote(server_name)}"


def find_mcp_proxy() -> Optional[str]:
    """Find the mcp-proxy executable in PATH."""
    return shutil.which("mcp-proxy")


def wait_for_random_port(process: subprocess.Popen, timeout: int = 20) -> Optional[int]:
    """
    Wait for mcp-proxy to output the random port information.

    Args:
        process: The mcp-proxy process
        timeout: Maximum time to wait in seconds

    Returns:
        The detected port number or None if not found
    """
    console.print("[cyan]Waiting for mcp-proxy to start...[/]")

    # Wait for mcp-proxy to output the port information
    start_time = time.time()
    port_found = False
    actual_port = None

    # Port detection loop
    while time.time() - start_time < timeout and not port_found:
        # Check if process is still running
        if process.poll() is not None:
            # Process terminated prematurely
            stderr_output = ""
            try:
                if process.stderr:
                    stderr_output = process.stderr.read() or ""
            except (IOError, OSError):
                pass

            console.print("[bold red]Error:[/] mcp-proxy terminated unexpectedly")
            console.print(f"[red]Error output:[/]\n{stderr_output}")
            sys.exit(1)

        # Process available output
        try:
            if process.stderr:
                line = process.stderr.readline()
                if line:
                    console.print(line.rstrip())

                # Check for port information
                if "Uvicorn running on http://" in line:
                    try:
                        url_part = line.split("Uvicorn running on ")[1].split(" ")[0]
                        actual_port = int(url_part.split(":")[-1].strip())
                        port_found = True
                        console.print(f"[cyan]mcp-proxy SSE server running on port [bold]{actual_port}[/bold][/]")
                        break
                    except (ValueError, IndexError):
                        pass
        except (IOError, OSError):
            # Resource temporarily unavailable - this is normal for non-blocking IO
            pass
        else:
            # No streams to read from, just wait a bit
            time.sleep(0.5)

    return actual_port


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
        console.print("  - uv tool install mcp-proxy")
        console.print("  - pip install mcp-proxy")
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
        actual_port = wait_for_random_port(process)

        # Check if we found the port
        if not actual_port:
            console.print("[bold red]Error:[/] Could not determine the port mcp-proxy is running on")
            process.terminate()
            sys.exit(1)

    return process, actual_port


def terminate_process(process: subprocess.Popen, timeout: int = 10) -> bool:
    """
    Safely terminate a process with escalating force if needed.

    Args:
        process: The process to terminate
        timeout: How long to wait before escalating to SIGKILL

    Returns:
        True if process terminated successfully, False otherwise
    """
    if process.poll() is not None:
        return True  # Already terminated

    try:
        # First try SIGTERM
        process.terminate()

        # Give process time to terminate gracefully
        for _ in range(timeout * 10):  # timeout * 10 * 0.1 = timeout seconds
            if process.poll() is not None:
                return True
            time.sleep(0.1)

        # If still running, use SIGKILL
        if process.poll() is None:
            console.print("[yellow]Process not responding to termination signal, forcing shutdown...[/]")
            process.kill()

            # Wait a bit more
            for _ in range(30):  # 3 seconds
                if process.poll() is not None:
                    return True
                time.sleep(0.1)

            # If still running after SIGKILL, something is very wrong
            if process.poll() is None:
                console.print("[bold red]Warning:[/] Process could not be terminated even with SIGKILL")
                return False
    except Exception as e:
        console.print(f"[yellow]Warning: Error during process cleanup: {str(e)}[/]")
        return False

    return True


def monitor_for_errors(line: str) -> Optional[str]:
    """
    Monitor process output for known error patterns.

    Args:
        line: A line of output to check

    Returns:
        An error message if an error is detected, None otherwise
    """
    known_errors = [
        (
            "RuntimeError: Received request before initialization was complete",
            "Protocol initialization error detected. This is a known issue with mcp-proxy.",
        ),
        ("anyio.BrokenResourceError", "Connection broken unexpectedly. The client may have disconnected."),
        ("ExceptionGroup: unhandled errors in a TaskGroup", "Server task error detected."),
    ]

    for error_pattern, message in known_errors:
        if error_pattern in line:
            return message

    return None


@click.command()
@click.argument("server_name", type=str)
@click.option("--port", type=int, default=None, help="Port for the SSE server (random if not specified)")
@click.option("--address", type=str, default=None, help="Remote address for tunnel, use share.mcpm.sh if not specified")
@click.option(
    "--http", is_flag=True, default=False, help="Use HTTP instead of HTTPS. NOT recommended to use on public networks."
)
@click.option(
    "--timeout",
    type=int,
    default=30,
    help="Timeout in seconds to wait for server requests before considering the server inactive",
)
@click.option("--retry", type=int, default=0, help="Number of times to automatically retry on error (default: 0)")
@click.help_option("-h", "--help")
def share(server_name, port, address, http, timeout, retry):
    """Share a server from global configuration through a tunnel.

    This command finds an installed server in the global configuration,
    uses mcp-proxy to expose it as an SSE server, then creates a tunnel
    to make it accessible remotely.

    SERVER_NAME is the name of an installed server from your global configuration.

    Examples:

    \b
        mcpm share time                    # Share the time server
        mcpm share mcp-server-browse       # Share the browse server  
        mcpm share filesystem --port 5000  # Share filesystem server on specific port
        mcpm share sqlite --retry 3        # Share with auto-retry on errors
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
    
    # Build the command to run the server
    command = build_server_command(server_config, server_name)
    
    if not command:
        console.print(f"[red]Error: Invalid server configuration for '{server_name}'[/]")
        sys.exit(1)
    
    # Show server info
    console.print(f"[dim]Found server '{server_name}' in {location} configuration[/]")
    console.print(f"[dim]Server will be launched via: {command}[/]")

    # Default to standard share address if not specified
    if not address:
        address = DEFAULT_SHARE_ADDRESS
        console.print(f"[cyan]Using default share address: {address}[/]")

    # Split remote host and port
    remote_host, remote_port = address.split(":")
    remote_port = int(remote_port)

    # Prepare to handle retries
    retries_left = retry
    should_retry = True

    while should_retry:
        server_process = None
        tunnel = None

        try:
            # Start mcp-proxy to convert stdio to SSE
            console.print(f"[cyan]Starting mcp-proxy to share server '[bold]{server_name}[/bold]'...[/]")
            server_process, actual_port = start_mcp_proxy(command, port)
            console.print(f"[cyan]mcp-proxy SSE server running on port [bold]{actual_port}[/bold][/]")

            # Create and start the tunnel
            console.print(f"[cyan]Creating tunnel from localhost:{actual_port} to {remote_host}:{remote_port}...[/]")
            # Always use empty string for token (equivalent to --no-secret)
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

            # Always show the warning about URL access
            console.print("[bold red]Warning:[/] Anyone with the URL can access your server.")

            console.print("[yellow]Press Ctrl+C to stop sharing and terminate the server[/]")

            # Track activity and errors
            last_activity_time = time.time()
            server_error_detected = False
            error_messages = []

            # Handle cleanup on termination signals
            def signal_handler(sig, frame):
                nonlocal should_retry
                should_retry = False  # Don't retry after explicit termination
                console.print("\n[yellow]Terminating server and tunnel...[/]")
                if tunnel:
                    console.print(f"[yellow]Killing tunnel localhost:{actual_port} <> {share_url}[/]")
                    tunnel.kill()

                if server_process and server_process.poll() is None:
                    terminate_process(server_process)

                # Only exit if not in retry mode
                if retries_left <= 0:
                    sys.exit(0)

            # Register signal handlers
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Keep the main process running and display server output
            while True:
                if server_process.poll() is not None:
                    if not server_error_detected:
                        console.print("[bold red]Server process terminated unexpectedly[/]")
                    if tunnel:
                        tunnel.kill()
                    break
                # Process available output
                try:
                    if server_process.stderr:
                        line = server_process.stderr.readline()
                        if line:
                            line_str = line.rstrip()
                            console.print(line_str)
                            last_activity_time = time.time()

                            # Check for error messages
                            error_msg = monitor_for_errors(line_str)
                            if error_msg and error_msg not in error_messages:
                                console.print(f"[bold red]Error:[/] {error_msg}")
                                error_messages.append(error_msg)
                                server_error_detected = True

                                # If this is a critical error and we have retries left, restart
                                if "Protocol initialization error" in error_msg and retries_left > 0:
                                    console.print(f"[yellow]Will attempt to restart ({retries_left} retries left)[/]")
                                    # Break out of the loop to trigger a restart
                                    server_process.terminate()
                                    break
                except (IOError, OSError):
                    # Resource temporarily unavailable - this is normal for non-blocking IO
                    pass
                else:
                    # No streams to read from, just wait a bit
                    time.sleep(0.5)

                # Check for inactivity timeout
                if timeout > 0 and time.time() - last_activity_time > timeout:
                    console.print(
                        f"[yellow]No activity detected for {timeout} seconds, checking if server is still responsive...[/]"
                    )
                    # Reset timer so we don't continuously warn
                    last_activity_time = time.time()

            # If we got here, the server stopped or had an error
            should_retry = server_error_detected and retries_left > 0

        except Exception as e:
            console.print(f"[bold red]Error:[/] {str(e)}")
            # Determine if we should retry
            should_retry = retries_left > 0

        # Clean up resources before retrying or exiting
        if server_process and server_process.poll() is None:
            terminate_process(server_process)

        if tunnel:
            tunnel.kill()

        # Manage retries
        if should_retry:
            retries_left -= 1
            console.print(f"[yellow]Retrying in 3 seconds... ({retries_left} attempts left)[/]")
            time.sleep(3)
        elif retries_left > 0:
            # We still have retries but chose not to use them (e.g. clean exit)
            console.print("[green]Server stopped cleanly, no need to retry.[/]")
            break
