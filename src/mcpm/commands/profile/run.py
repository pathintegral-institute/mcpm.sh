"""Profile run command."""

import asyncio
import logging

from rich.console import Console
from rich.panel import Panel

from mcpm.fastmcp_integration.proxy import create_mcpm_proxy

# Removed SessionAction import - using strings directly
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.config import DEFAULT_PORT
from mcpm.utils.logging_config import (
    ensure_dependency_logging_suppressed,
    get_uvicorn_log_level,
    setup_dependency_logging,
)
from mcpm.utils.rich_click_config import click

profile_config_manager = ProfileConfigManager()
logger = logging.getLogger(__name__)
console = Console()


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


async def run_profile_fastmcp(profile_servers, profile_name, http_mode=False, port=DEFAULT_PORT, host="127.0.0.1"):
    """Run profile servers using FastMCP proxy for proper aggregation."""
    server_count = len(profile_servers)
    logger.debug(f"Using FastMCP proxy to aggregate {server_count} server(s)")
    logger.debug(f"Mode: {'HTTP' if http_mode else 'stdio'}")

    try:
        # Create FastMCP proxy for profile servers
        proxy = await create_mcpm_proxy(
            servers=profile_servers,
            name=f"profile-{profile_name}",
            stdio_mode=not http_mode,  # stdio_mode=False for HTTP
            action="profile_run",
            profile_name=profile_name,
        )

        logger.debug(f"FastMCP proxy initialized with: {[s.name for s in profile_servers]}")

        # Set up dependency logging for FastMCP/MCP libraries
        setup_dependency_logging()

        # Re-suppress library logging after FastMCP initialization
        ensure_dependency_logging_suppressed()

        # Note: Usage tracking is handled by proxy middleware

        if http_mode:
            # Try to find an available port if the requested one is taken
            actual_port = await find_available_port(port)
            if actual_port != port:
                logger.debug(f"Port {port} is busy, using port {actual_port} instead")

            # Display profile information in a nice panel
            http_url = f"http://{host}:{actual_port}/mcp/"

            # Build server list
            server_list = "\n".join([f"  • [cyan]{server.name}[/]" for server in profile_servers])

            panel_content = f"[bold]Profile:[/] {profile_name}\n[bold]URL:[/] [cyan]{http_url}[/cyan]\n\n[bold]Servers:[/]\n{server_list}\n\n[dim]Press Ctrl+C to stop the profile[/]"

            panel = Panel(
                panel_content,
                title="📁 Profile Running Locally",
                title_align="left",
                border_style="green",
                padding=(1, 2),
            )
            console.print(panel)

            logger.debug(f"Starting FastMCP proxy for profile '{profile_name}' on {host}:{actual_port}")

            # Run the aggregated proxy over HTTP with uvicorn logging control
            await proxy.run_http_async(
                host=host, port=actual_port, uvicorn_config={"log_level": get_uvicorn_log_level()}
            )
        else:
            # Run the aggregated proxy over stdio (default)
            logger.info(f"Starting profile '{profile_name}' over stdio")
            await proxy.run_stdio_async()

        return 0

    except KeyboardInterrupt:
        logger.info("Profile execution interrupted")
        return 130
    except Exception as e:
        logger.error(f"Error running profile '{profile_name}': {e}")
        return 1


@click.command()
@click.argument("profile_name")
@click.option("--http", is_flag=True, help="Run profile over HTTP instead of stdio")
@click.option("--port", type=int, default=DEFAULT_PORT, help=f"Port for HTTP mode (default: {DEFAULT_PORT})")
@click.option("--host", type=str, default="127.0.0.1", help="Host address for HTTP mode (default: 127.0.0.1)")
@click.help_option("-h", "--help")
def run(profile_name, http, port, host):
    """Execute all servers in a profile over stdio or HTTP.

    Uses FastMCP proxy to aggregate servers into a unified MCP interface
    with proper capability namespacing. By default runs over stdio.

    Examples:

    \b
        mcpm profile run web-dev                          # Run over stdio (default)
        mcpm profile run --http web-dev                   # Run over HTTP on 127.0.0.1:6276
        mcpm profile run --http --port 9000 ai            # Run over HTTP on 127.0.0.1:9000
        mcpm profile run --http --host 0.0.0.0 web-dev    # Run over HTTP on 0.0.0.0:6276

    Debug logging: Set MCPM_DEBUG=1 for verbose output
    """
    # Validate profile name
    if not profile_name or not profile_name.strip():
        logger.error("Profile name cannot be empty")
        return 1

    profile_name = profile_name.strip()

    # Check if profile exists
    try:
        profile_servers = profile_config_manager.get_profile(profile_name)
        if profile_servers is None:
            logger.error(f"Profile '{profile_name}' not found")
            logger.info("Available options:")
            logger.info("  • Run 'mcpm profile ls' to see available profiles")
            logger.info("  • Run 'mcpm profile create {name}' to create a profile")
            return 1
    except Exception as e:
        logger.error(f"Error accessing profile '{profile_name}': {e}")
        return 1

    if not profile_servers:
        logger.warning(f"Profile '{profile_name}' has no servers configured")
        logger.info("Add servers to this profile with:")
        logger.info(f"  mcpm profile edit {profile_name}")
        return 0

    logger.info(f"Running profile '{profile_name}' with {len(profile_servers)} server(s)")

    # Log debug info about servers (controlled by MCPM_DEBUG environment variable)
    logger.debug("Servers to run:")
    for server_config in profile_servers:
        logger.debug(f"  - {server_config.name}: {server_config}")

    # Use FastMCP proxy for all cases (single or multiple servers)
    logger.debug(f"Using FastMCP proxy for {len(profile_servers)} server(s)")
    if http:
        logger.debug(f"HTTP mode on port {port}")

    # Run the async function
    return asyncio.run(run_profile_fastmcp(profile_servers, profile_name, http_mode=http, port=port, host=host))
