"""Profile run command."""

import asyncio
import logging

import click

from mcpm.fastmcp_integration.proxy import create_mcpm_proxy
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.config import DEFAULT_PORT

profile_config_manager = ProfileConfigManager()
logger = logging.getLogger(__name__)


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


async def run_profile_fastmcp(profile_servers, profile_name, debug=False, http_mode=False, port=DEFAULT_PORT):
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
        )

        logger.debug(f"FastMCP proxy initialized with: {[s.name for s in profile_servers]}")

        # Record profile usage
        from mcpm.commands.usage import record_profile_usage

        record_profile_usage(profile_name, "run" + ("_http" if http_mode else ""))

        if http_mode:
            # Try to find an available port if the requested one is taken
            actual_port = await find_available_port(port)
            if actual_port != port:
                logger.warning(f"Port {port} is busy, using port {actual_port} instead")

            logger.info(f"Starting profile '{profile_name}' on HTTP port {actual_port}")
            logger.info("Press Ctrl+C to stop the profile.")

            # Run the aggregated proxy over HTTP
            await proxy.run_streamable_http_async(host="127.0.0.1", port=actual_port)
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
@click.option("--debug", is_flag=True, help="Show debug output")
@click.option("--http", is_flag=True, help="Run profile over HTTP instead of stdio")
@click.option("--port", type=int, default=8000, help="Port for HTTP mode (default: 8000)")
@click.help_option("-h", "--help")
def run(profile_name, debug, http, port):
    """Execute all servers in a profile over stdio or HTTP.

    Uses FastMCP proxy to aggregate servers into a unified MCP interface
    with proper capability namespacing. By default runs over stdio.

    Examples:

    \b
        mcpm profile run web-dev                    # Run over stdio (default)
        mcpm profile run --http web-dev             # Run over HTTP on port 8000
        mcpm profile run --http --port 9000 ai      # Run over HTTP on port 9000
        mcpm profile run --debug --http web-dev     # Debug + HTTP mode
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

    if debug:
        logging.basicConfig(level=logging.DEBUG)

    # Only show visual output in debug mode or HTTP mode
    if debug or http:
        logger.info(f"Running profile '{profile_name}' with {len(profile_servers)} server(s)")

        if debug:
            logger.debug("Servers to run:")
            for server_config in profile_servers:
                logger.debug(f"  - {server_config.name}: {server_config}")

    # Use FastMCP proxy for all cases (single or multiple servers)
    logger.debug(f"Using FastMCP proxy for {len(profile_servers)} server(s)")
    if http:
        logger.debug(f"HTTP mode on port {port}")

    # Run the async function
    return asyncio.run(run_profile_fastmcp(profile_servers, profile_name, debug, http_mode=http, port=port))
