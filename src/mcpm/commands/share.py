"""
Share command for MCPM - Share a single MCP server through a tunnel
"""

import asyncio
import secrets
import sys
from typing import Optional

import click
from rich.console import Console

from mcpm.global_config import GlobalConfigManager
from mcpm.fastmcp_integration.proxy import create_mcpm_proxy
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


async def find_available_port(preferred_port, max_attempts=10):
    """Find an available port starting from preferred_port."""
    import socket
    
    for attempt in range(max_attempts):
        port_to_try = preferred_port + attempt
        
        # Check if port is available
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port_to_try))
                return port_to_try
        except OSError:
            continue  # Port is busy, try next one
    
    # If no port found, return the original (will likely fail but user will see the error)
    return preferred_port


async def start_fastmcp_proxy(server_config, server_name, port: Optional[int] = None) -> int:
    """
    Start FastMCP proxy in HTTP mode for sharing a single server.

    Args:
        server_config: The server configuration
        server_name: The server name
        port: Preferred port number (finds available port if None or busy)

    Returns:
        The actual port number the proxy is running on
    """
    # Use default port if none specified
    preferred_port = port or 8000
    
    # Find an available port
    actual_port = await find_available_port(preferred_port)
    if actual_port != preferred_port:
        console.print(f"[yellow]Port {preferred_port} is busy, using port {actual_port} instead[/]")
    
    console.print(f"[cyan]Starting FastMCP proxy for server '{server_name}' on port {actual_port}...[/]")
    
    try:
        # Record usage
        from mcpm.commands.usage import record_server_usage
        record_server_usage(server_name, "share")
        
        # Create FastMCP proxy for single server (HTTP mode for sharing)
        proxy = await create_mcpm_proxy(
            servers=[server_config],
            name=f"mcpm-share-{server_name}",
            stdio_mode=False  # HTTP mode for sharing
        )
        
        console.print(f"[green]FastMCP proxy ready on port {actual_port}[/]")
        
        # Return the port and proxy instance
        return actual_port, proxy
        
    except Exception as e:
        console.print(f"[red]Error starting FastMCP proxy: {e}[/]")
        raise


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
    uses FastMCP proxy to expose it as an HTTP server, then creates a tunnel
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
    
    # Show server info
    console.print(f"[dim]Found server '{server_name}' in {location} configuration[/]")

    # Default to standard share address if not specified
    if not address:
        address = DEFAULT_SHARE_ADDRESS
        console.print(f"[cyan]Using default share address: {address}[/]")

    # Split remote host and port
    remote_host, remote_port = address.split(":")
    remote_port = int(remote_port)

    # Run the async function to start proxy and create tunnel
    asyncio.run(_share_async(server_config, server_name, port, remote_host, remote_port, http, timeout, retry))


async def _share_async(server_config, server_name, port, remote_host, remote_port, http, timeout, retry):
    """Async function to handle sharing with FastMCP proxy."""
    import signal
    import time
    
    # Prepare to handle retries
    retries_left = retry
    should_retry = True

    while should_retry:
        proxy = None
        tunnel = None

        try:
            # Start FastMCP proxy
            console.print(f"[cyan]Starting FastMCP proxy to share server '[bold]{server_name}[/bold]'...[/]")
            actual_port, proxy = await start_fastmcp_proxy(server_config, server_name, port)

            # Create and start the tunnel
            console.print(f"[cyan]Creating tunnel from localhost:{actual_port} to {remote_host}:{remote_port}...[/]")
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

            # Display the share URL
            console.print(f"[bold green]Server is now shared at: [/][bold cyan]{share_url}[/]")

            # Always show the warning about URL access
            console.print("[bold red]Warning:[/] Anyone with the URL can access your server.")

            console.print("[yellow]Press Ctrl+C to stop sharing and terminate the server[/]")

            # Track activity
            last_activity_time = time.time()
            server_error_detected = False

            # Handle cleanup on termination signals
            def signal_handler(sig, frame):
                nonlocal should_retry
                should_retry = False  # Don't retry after explicit termination
                console.print("\n[yellow]Terminating server and tunnel...[/]")
                if tunnel:
                    console.print(f"[yellow]Killing tunnel localhost:{actual_port} <> {share_url}[/]")
                    tunnel.kill()

                # Only exit if not in retry mode
                if retries_left <= 0:
                    sys.exit(0)

            # Register signal handlers
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Run the HTTP server
            try:
                await proxy.run_streamable_http_async(port=actual_port)
            except Exception as e:
                if "Protocol initialization error" in str(e) and retries_left > 0:
                    console.print(f"[yellow]Will attempt to restart ({retries_left} retries left)[/]")
                    server_error_detected = True
                else:
                    raise

            # If we got here, the server stopped or had an error
            should_retry = server_error_detected and retries_left > 0

        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping server and tunnel...[/]")
            should_retry = False
        except Exception as e:
            console.print(f"[bold red]Error:[/] {str(e)}")
            # Determine if we should retry
            should_retry = retries_left > 0

        # Clean up resources before retrying or exiting
        if tunnel:
            tunnel.kill()

        # Manage retries
        if should_retry:
            retries_left -= 1
            console.print(f"[yellow]Retrying in 3 seconds... ({retries_left} attempts left)[/]")
            await asyncio.sleep(3)
        elif retries_left > 0:
            # We still have retries but chose not to use them (e.g. clean exit)
            console.print("[green]Server stopped cleanly, no need to retry.[/]")
            break