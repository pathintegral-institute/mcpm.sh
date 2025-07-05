"""Profile share command."""

import asyncio
import logging
import secrets

from rich.console import Console
from rich.panel import Panel

from mcpm.core.tunnel import Tunnel
from mcpm.fastmcp_integration.proxy import create_mcpm_proxy
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.config import DEFAULT_PORT, DEFAULT_SHARE_ADDRESS
from mcpm.utils.logging_config import (
    ensure_dependency_logging_suppressed,
    get_uvicorn_log_level,
    setup_dependency_logging,
)
from mcpm.utils.rich_click_config import click

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


async def share_profile_fastmcp(profile_servers, profile_name, port, address, http, no_auth):
    """Share profile servers using FastMCP proxy + tunnel."""
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
        server_count = len(profile_servers)
        logger.debug(f"Creating FastMCP proxy for profile '{profile_name}' with {server_count} server(s)")

        # Create FastMCP proxy for profile servers (HTTP mode - disable auth)
        proxy = await create_mcpm_proxy(
            servers=profile_servers,
            name=f"shared-profile-{profile_name}",
            stdio_mode=False,  # HTTP mode for sharing
            auth_enabled=not no_auth,
            api_key=api_key,
        )

        logger.debug(f"FastMCP proxy created with {server_count} server(s)")

        # Set up dependency logging for FastMCP/MCP libraries
        setup_dependency_logging()

        # Re-suppress library logging after FastMCP initialization
        ensure_dependency_logging_suppressed()

        # Use default port if none specified, then find available port
        preferred_port = port or DEFAULT_PORT
        actual_port = await find_available_port(preferred_port)
        if actual_port != preferred_port:
            logger.debug(f"Port {preferred_port} is busy, using port {actual_port} instead")

        logger.debug(f"Starting HTTP server on port {actual_port}")

        # Start the FastMCP proxy as a streamable HTTP server in a background task
        server_task = asyncio.create_task(
            proxy.run_http_async(
                host="127.0.0.1", port=actual_port, uvicorn_config={"log_level": get_uvicorn_log_level()}
            )
        )

        # Wait a moment for server to start
        await asyncio.sleep(2)

        logger.debug(f"FastMCP proxy running on port {actual_port}")

        # Create tunnel to make it publicly accessible
        if not address:
            address = DEFAULT_SHARE_ADDRESS

        remote_host, remote_port = address.split(":")
        logger.debug(f"Creating tunnel from localhost:{actual_port} to {remote_host}:{remote_port}")

        # Generate a random share token
        share_token = secrets.token_urlsafe(32)

        tunnel = Tunnel(
            remote_host=remote_host,
            remote_port=int(remote_port),
            local_host="localhost",
            local_port=actual_port,
            share_token=share_token,
            http=http,
            share_server_tls_certificate=None,
        )

        public_url = tunnel.start_tunnel()

        if public_url:
            # Display critical information in a nice panel
            http_url = f"{public_url}/mcp/"

            # Build server list
            server_list = "\n".join([f"  • [cyan]{server.name}[/]" for server in profile_servers])

            # Build panel content based on auth status
            panel_content = f"[bold]Profile:[/] {profile_name}\n[bold]URL:[/] [cyan]{http_url}[/cyan]\n"

            if not no_auth and api_key:
                panel_content += f"[bold]HEADER Authorization:[/] [cyan]Bearer {api_key}[/cyan]\n"
            else:
                panel_content += "[bold red]⚠️  Warning:[/] Anyone with the URL can access your servers\n"

            panel_content += f"\n[bold]Shared servers:[/]\n{server_list}\n\n[dim]Press Ctrl+C to stop sharing[/]"

            panel = Panel(
                panel_content,
                title="📁 Profile Shared Publicly",
                title_align="left",
                border_style="blue",
                padding=(1, 2),
            )
            console.print(panel)

            # Keep running until interrupted
            try:
                await server_task
            except asyncio.CancelledError:
                pass
            finally:
                if tunnel:
                    tunnel.kill()
        else:
            console.print("[red]Failed to create tunnel[/]")
            logger.error("Failed to create tunnel")
            server_task.cancel()
            # Wait for cancellation to complete
            await asyncio.gather(server_task, return_exceptions=True)
            return 1

        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping...[/]")
        return 130
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        logger.exception("Detailed error information")
        return 1


@click.command(name="share")
@click.argument("profile_name")
@click.option("--port", type=int, default=None, help="Port for the SSE server (random if not specified)")
@click.option("--address", type=str, default=None, help="Remote address for tunnel, use share.mcpm.sh if not specified")
@click.option(
    "--http", is_flag=True, default=False, help="Use HTTP instead of HTTPS. NOT recommended to use on public networks."
)
@click.option("--no-auth", is_flag=True, default=False, help="Disable authentication for the shared profile.")
@click.help_option("-h", "--help")
def share_profile(profile_name, port, address, http, no_auth):
    """Create a secure public tunnel to all servers in a profile.

    This command runs all servers in a profile and creates a shared tunnel
    to make them accessible remotely. Each server gets its own endpoint.

    Examples:

    \b
        mcpm profile share web-dev           # Share all servers in web-dev profile
        mcpm profile share ai --port 5000    # Share ai profile on specific port
    """
    # Check if profile exists
    profile_servers = profile_config_manager.get_profile(profile_name)
    if profile_servers is None:
        console.print(f"[red]Error: Profile '[bold]{profile_name}[/]' not found[/]")
        console.print()
        console.print("[yellow]Available options:[/]")
        console.print("  • Run 'mcpm profile ls' to see available profiles")
        console.print("  • Run 'mcpm profile create {name}' to create a profile")
        return 1

    # Get servers in profile
    if not profile_servers:
        console.print(f"[yellow]Profile '[bold]{profile_name}[/]' has no servers configured[/]")
        console.print()
        console.print("[dim]Add servers to this profile with:[/]")
        console.print(f"  mcpm profile edit {profile_name}")
        return 0

    console.print(f"[bold green]Sharing profile '[cyan]{profile_name}[/]' with {len(profile_servers)} server(s)[/]")

    # Use FastMCP proxy for all cases (single or multiple servers)
    console.print(f"[cyan]Setting up FastMCP proxy for {len(profile_servers)} server(s)...[/]")
    return asyncio.run(share_profile_fastmcp(profile_servers, profile_name, port, address, http, no_auth))
