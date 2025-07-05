"""
Share command for MCPM - Share a single MCP server through a tunnel
"""

import asyncio
import logging
import secrets
import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from mcpm.core.tunnel import Tunnel
from mcpm.fastmcp_integration.proxy import create_mcpm_proxy
from mcpm.global_config import GlobalConfigManager

# Removed SessionAction import - using strings directly
from mcpm.utils.config import DEFAULT_PORT, DEFAULT_SHARE_ADDRESS
from mcpm.utils.logging_config import (
    ensure_dependency_logging_suppressed,
    get_uvicorn_log_level,
    setup_dependency_logging,
)
from mcpm.utils.rich_click_config import click

console = Console()
global_config_manager = GlobalConfigManager()
logger = logging.getLogger(__name__)


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
                s.bind(("127.0.0.1", port_to_try))
                return port_to_try
        except OSError:
            continue  # Port is busy, try next one

    # If no port found, return the original (will likely fail but user will see the error)
    return preferred_port


async def start_fastmcp_proxy(
    server_config, server_name, port: Optional[int] = None, auth_enabled: bool = True, api_key: Optional[str] = None
) -> int:
    """
    Start FastMCP proxy in HTTP mode for sharing a single server.

    Args:
        server_config: The server configuration
        server_name: The server name
        port: Preferred port number (finds available port if None or busy)
        auth_enabled: Whether to enable authentication
        api_key: The API key to use for authentication

    Returns:
        The actual port number the proxy is running on
    """
    # Use default port if none specified
    preferred_port = port or DEFAULT_PORT

    # Find an available port
    actual_port = await find_available_port(preferred_port)
    if actual_port != preferred_port:
        logger.debug(f"Port {preferred_port} is busy, using port {actual_port} instead")

    logger.debug(f"Starting FastMCP proxy for server '{server_name}' on port {actual_port}")

    try:
        # Note: Usage tracking is handled by proxy middleware

        # Create FastMCP proxy for single server (HTTP mode for sharing)
        proxy = await create_mcpm_proxy(
            servers=[server_config],
            name=f"mcpm-share-{server_name}",
            stdio_mode=False,  # HTTP mode for sharing
            auth_enabled=auth_enabled,
            api_key=api_key,
            action="share",
        )

        logger.debug(f"FastMCP proxy ready on port {actual_port}")

        # Set up dependency logging for FastMCP/MCP libraries
        setup_dependency_logging()

        # Re-suppress library logging after FastMCP initialization
        ensure_dependency_logging_suppressed()

        # Return the port and proxy instance
        return actual_port, proxy

    except Exception as e:
        logger.error(f"Error starting FastMCP proxy: {e}")
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
@click.option("--no-auth", is_flag=True, default=False, help="Disable authentication for the shared server.")
@click.help_option("-h", "--help")
def share(server_name, port, address, http, timeout, retry, no_auth):
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
    asyncio.run(_share_async(server_config, server_name, port, remote_host, remote_port, http, timeout, retry, no_auth))


async def _share_async(server_config, server_name, port, remote_host, remote_port, http, timeout, retry, no_auth):
    """Async function to handle sharing with FastMCP proxy."""

    proxy = None
    tunnel = None
    server_task = None
    api_key = None

    if not no_auth:
        from mcpm.utils.config import ConfigManager

        config_manager = ConfigManager()
        auth_config = config_manager.get_auth_config()
        api_key = auth_config.get("api_key")
        if not api_key:
            api_key = secrets.token_urlsafe(32)
            config_manager.save_auth_config(api_key)
            console.print(f"[green]Generated new API key:[/] [cyan]{api_key}[/]")

    try:
        # Start FastMCP proxy
        logger.debug(f"Starting FastMCP proxy to share server '{server_name}'")
        actual_port, proxy = await start_fastmcp_proxy(
            server_config, server_name, port, auth_enabled=not no_auth, api_key=api_key
        )

        # Start the FastMCP proxy as an HTTP server in a background task
        server_task = asyncio.create_task(
            proxy.run_http_async(port=actual_port, uvicorn_config={"log_level": get_uvicorn_log_level()})
        )

        # Wait a moment for server to start
        await asyncio.sleep(2)

        # Create and start the tunnel
        logger.debug(f"Creating tunnel from localhost:{actual_port} to {remote_host}:{remote_port}")
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

        if not share_url:
            raise RuntimeError("Could not get share URL from tunnel.")

        # Display critical information in a nice panel
        http_url = f"{share_url}/mcp/"

        # Build panel content based on auth status
        panel_content = f"[bold]Server:[/] {server_name}\n[bold]URL:[/] [cyan]{http_url}[/cyan]\n"

        if not no_auth and api_key:
            panel_content += f"[bold]HEADER Authorization:[/] [cyan]Bearer {api_key}[/cyan]\n"
        else:
            panel_content += "[bold red]⚠️  Warning:[/] Anyone with the URL can access your server\n"

        panel_content += "\n[dim]Press Ctrl+C to stop sharing[/]"

        panel = Panel(
            panel_content, title="🌍 Server Shared Publicly", title_align="left", border_style="blue", padding=(1, 2)
        )
        console.print(panel)

        # Keep running until interrupted
        await server_task

    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print("\n[yellow]Stopping...[/]")
    except Exception as e:
        console.print(f"[bold red]Error: {e}[/]")
        logger.exception("Detailed error information")
    finally:
        if tunnel:
            tunnel.kill()
        if server_task and not server_task.done():
            server_task.cancel()
        logger.debug("Sharing stopped")
