"""Profile share command."""

import click
from rich.console import Console

from mcpm.profile.profile_config import ProfileConfigManager

console = Console()
profile_config_manager = ProfileConfigManager()


@click.command(name="share")
@click.argument("profile_name")
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
def share_profile(profile_name, port, address, http, timeout, retry):
    """Create a secure public tunnel to all servers in a profile.

    This command runs all servers in a profile and creates a shared tunnel
    to make them accessible remotely. Each server gets its own endpoint.

    Examples:

    \\b
        mcpm profile share web-dev           # Share all servers in web-dev profile
        mcpm profile share ai --port 5000    # Share ai profile on specific port
        mcpm profile share data --retry 3    # Share with retry on errors
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

    # For now, we'll use the router approach or share the first server
    # In a full implementation, this would set up a multiplexed sharing system
    if len(profile_servers) == 1:
        # Single server - use direct sharing
        server_config = profile_servers[0]
        server_dict = server_config.model_dump()

        if "command" not in server_dict:
            console.print(f"[red]Error: Server '{server_config.name}' has no command specified[/]")
            return 1

        command = server_dict["command"]
        if isinstance(command, list):
            command_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in command)
        else:
            command_str = str(command)

        console.print(f"[cyan]Sharing server: {server_config.name}[/]")
        console.print(f"[dim]Command: {command_str}[/]")

        # Import and call the share command
        from mcpm.commands.share import share

        # Create a context and invoke the share command
        ctx = click.Context(share)
        ctx.invoke(share, command=command_str, port=port, address=address, http=http, timeout=timeout, retry=retry)

    else:
        # Multiple servers - would need router or multiplexed approach
        console.print("[yellow]Multi-server profile sharing not yet implemented.[/]")
        console.print("[dim]For now, you can share individual servers with 'mcpm share <server-name>'[/]")
        console.print()
        console.print("[cyan]Servers in this profile:[/]")
        for server_config in profile_servers:
            console.print(f"  • {server_config.name}")

        return 1
