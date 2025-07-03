"""Profile run command."""

import asyncio
import logging

import click
from rich.console import Console

from mcpm.fastmcp_integration.proxy import create_mcpm_proxy
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.config import DEFAULT_PORT

console = Console()
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
    if debug:
        debug_console = Console(stderr=True)
        debug_console.print(f"[dim]Using FastMCP proxy to aggregate {server_count} server(s)[/]")
        debug_console.print(f"[dim]Mode: {'HTTP' if http_mode else 'stdio'}[/]")

    try:
        # Create FastMCP proxy for profile servers
        proxy = await create_mcpm_proxy(
            servers=profile_servers,
            name=f"profile-{profile_name}",
            stdio_mode=not http_mode,  # stdio_mode=False for HTTP
        )

        if debug:
            debug_console = Console(stderr=True)
            debug_console.print(f"[dim]FastMCP proxy initialized with: {[s.name for s in profile_servers]}[/]")

        # Record profile usage
        from mcpm.commands.usage import record_profile_usage

        record_profile_usage(profile_name, "run" + ("_http" if http_mode else ""))

        if http_mode:
            # Try to find an available port if the requested one is taken
            actual_port = await find_available_port(port)
            if actual_port != port:
                logger.warning(f"Port {port} is busy, using port {actual_port} instead")
                if debug:
                    debug_console = Console(stderr=True)
                    debug_console.print(f"[yellow]Port {port} is busy, using port {actual_port} instead[/]")

            logger.info(f"Starting profile '{profile_name}' on HTTP port {actual_port}")
            if debug:
                debug_console = Console(stderr=True)
                debug_console.print(f"[cyan]Starting profile '{profile_name}' on HTTP port {actual_port}...[/]")
                debug_console.print("[yellow]Press Ctrl+C to stop the profile.[/]")

            # Run the aggregated proxy over HTTP
            await proxy.run_streamable_http_async(host="127.0.0.1", port=actual_port)
        else:
            # Run the aggregated proxy over stdio (default)
            logger.info(f"Starting profile '{profile_name}' over stdio")
            await proxy.run_stdio_async()

        return 0

    except KeyboardInterrupt:
        logger.info("Profile execution interrupted")
        if debug:
            debug_console = Console(stderr=True)
            debug_console.print("\n[yellow]Profile execution interrupted[/]")
        return 130
    except Exception as e:
        logger.error(f"Error running profile '{profile_name}': {e}")
        # For errors, still use console.print as we need to show the error to user
        console.print(f"[red]Error running profile '{profile_name}': {e}[/]")
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

    \\b
        mcpm profile run web-dev                    # Run over stdio (default)
        mcpm profile run --http web-dev             # Run over HTTP on port 8000
        mcpm profile run --http --port 9000 ai      # Run over HTTP on port 9000
        mcpm profile run --debug --http web-dev     # Debug + HTTP mode
    """
    # Validate profile name
    if not profile_name or not profile_name.strip():
        console.print("[red]Error: Profile name cannot be empty[/]")
        return 1

    profile_name = profile_name.strip()

    # Check if profile exists
    try:
        profile_servers = profile_config_manager.get_profile(profile_name)
        if profile_servers is None:
            console.print(f"[red]Error: Profile '[bold]{profile_name}[/]' not found[/]")
            console.print()
            console.print("[yellow]Available options:[/]")
            console.print("  • Run 'mcpm profile ls' to see available profiles")
            console.print("  • Run 'mcpm profile create {name}' to create a profile")
            return 1
    except Exception as e:
        console.print(f"[red]Error accessing profile '{profile_name}': {e}[/]")
        return 1

    if not profile_servers:
        console.print(f"[yellow]Profile '[bold]{profile_name}[/]' has no servers configured[/]")
        console.print()
        console.print("[dim]Add servers to this profile with:[/]")
        console.print(f"  mcpm profile edit {profile_name}")
        return 0

    logger.info(f"Running profile '{profile_name}' with {len(profile_servers)} server(s)")

    # Only show visual output in debug mode or HTTP mode
    if debug or http:
        debug_console = Console(stderr=True)
        debug_console.print(f"[bold green]Running profile '[cyan]{profile_name}[/]' with {len(profile_servers)} server(s)[/]")

        if debug:
            debug_console.print("[dim]Servers to run:[/]")
            for server_config in profile_servers:
                debug_console.print(f"  - {server_config.name}: {server_config}")

    # Use FastMCP proxy for all cases (single or multiple servers)
    if debug:
        debug_console = Console(stderr=True)
        debug_console.print(f"[dim]Using FastMCP proxy for {len(profile_servers)} server(s)[/]")
        if http:
            debug_console.print(f"[dim]HTTP mode on port {port}[/]")

    # Run the async function
    return asyncio.run(run_profile_fastmcp(profile_servers, profile_name, debug, http_mode=http, port=port))
