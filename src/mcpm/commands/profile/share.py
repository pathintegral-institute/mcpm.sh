"""Profile share command."""

import asyncio
import secrets

import click
from rich.console import Console

from mcpm.core.router_config import RouterConfig
from mcpm.core.tunnel import Tunnel
from mcpm.fastmcp_integration.proxy import create_mcpm_proxy
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.config import DEFAULT_SHARE_ADDRESS

console = Console()
profile_config_manager = ProfileConfigManager()


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


async def share_profile_fastmcp(profile_servers, profile_name, port, address, http):
    """Share profile servers using FastMCP proxy + tunnel."""
    try:
        console.print(f"[cyan]Creating FastMCP proxy for profile '{profile_name}'...[/]")

        # Create a router config with auth disabled for public sharing
        router_config = RouterConfig(auth_enabled=False)

        # Create FastMCP proxy for profile servers (HTTP mode - disable auth)
        proxy = await create_mcpm_proxy(
            servers=profile_servers,
            name=f"shared-profile-{profile_name}",
            stdio_mode=False,  # HTTP mode for sharing
            router_config=router_config,  # Pass config to disable auth
        )

        server_count = len(profile_servers)
        console.print(f"[green]FastMCP proxy created with {server_count} server(s)[/]")

        # Use default port if none specified, then find available port
        preferred_port = port or 8000
        actual_port = await find_available_port(preferred_port)
        if actual_port != preferred_port:
            console.print(f"[yellow]Port {preferred_port} is busy, using port {actual_port} instead[/]")

        console.print(f"[cyan]Starting streamable HTTP server on port {actual_port}...[/]")

        # Start the FastMCP proxy as a streamable HTTP server in a background task
        server_task = asyncio.create_task(proxy.run_streamable_http_async(host="127.0.0.1", port=actual_port))

        # Wait a moment for server to start
        await asyncio.sleep(2)

        console.print(f"[green]FastMCP proxy running on port {actual_port}[/]")

        # Create tunnel to make it publicly accessible
        if not address:
            address = DEFAULT_SHARE_ADDRESS

        remote_host, remote_port = address.split(":")

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

        console.print("[cyan]Creating secure tunnel...[/]")
        public_url = tunnel.start_tunnel()

        if public_url:
            console.print(f"[bold green]Profile '{profile_name}' is now publicly accessible![/]")
            console.print(f"[cyan]Public URL:[/] {public_url}")
            console.print()
            console.print("[bold]Connection URLs:[/]")
            console.print(f"  • Streamable HTTP: [cyan]{public_url}/mcp/[/]")
            console.print(f"  • SSE endpoint: [cyan]{public_url}/sse/[/]")
            console.print()
            console.print("[bold]Available servers in this profile:[/]")
            for server_config in profile_servers:
                console.print(f"  • {server_config.name}")
            console.print()
            console.print("[dim]Press Ctrl+C to stop sharing...[/]")

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
            server_task.cancel()
            # Wait for cancellation to complete
            await asyncio.gather(server_task, return_exceptions=True)
            return 1

        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping profile sharing...[/]")
        return 130
    except Exception as e:
        console.print(f"[red]Error sharing profile: {e}[/]")
        return 1


@click.command(name="share")
@click.argument("profile_name")
@click.option("--port", type=int, default=None, help="Port for the SSE server (random if not specified)")
@click.option("--address", type=str, default=None, help="Remote address for tunnel, use share.mcpm.sh if not specified")
@click.option(
    "--http", is_flag=True, default=False, help="Use HTTP instead of HTTPS. NOT recommended to use on public networks."
)
@click.help_option("-h", "--help")
def share_profile(profile_name, port, address, http):
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
    return asyncio.run(share_profile_fastmcp(profile_servers, profile_name, port, address, http))
