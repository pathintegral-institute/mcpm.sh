import click
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from mcpm.clients.client_registry import ClientRegistry
from mcpm.profile.profile_manager import ProfileManager

profile_manager = ProfileManager()
console = Console()


@click.group()
def profile():
    """Manage MCPM profiles."""
    pass


@click.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed server information")
def list(verbose=False):
    """List all MCPM profiles."""
    profiles = profile_manager.list_profiles()
    if not profiles:
        console.print("\n[yellow]No profiles found.[/]\n")
        return
    console.print(f"\n[green]Found {len(profiles)} profile(s)[/]\n")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Servers", overflow="fold")
    if verbose:
        table.add_column("Server Details", overflow="fold")
    for profile_name, configs in profiles.items():
        server_names = [config.name for config in configs]
        row = [profile_name, ", ".join(server_names)]
        if verbose:
            details = []
            for config in configs:
                details.append(f"{config.name}: {config.command} {' '.join(config.args)}")
            row.append("\n".join(details))
        table.add_row(*row)
    console.print(table)


@click.command()
@click.argument("profile")
@click.option("--force", is_flag=True, help="Force add even if profile already exists")
def add(profile, force=False):
    """Add a new MCPM profile."""
    if profile_manager.get_profile(profile) is not None and not force:
        console.print(f"[bold red]Error:[/] Profile '{profile}' already exists.")
        console.print("Use '--force' to overwrite the existing profile.")
        return

    profile_manager.new_profile(profile)

    console.print(f"\n[green]Profile '{profile}' added successfully.[/]\n")
    console.print(f"You can now add servers to this profile with 'mcpm add --profile {profile} <server_name>'\n")
    console.print(
        f"Or apply existing config to this profile with 'mcpm profile apply {profile} --server <server_name>'\n"
    )


@click.command()
@click.argument("profile")
@click.option("--server", "-s", required=True, help="Server to apply config to")
def apply(profile, server):
    """Apply an existing MCPM config to a profile."""
    client_manager = ClientRegistry.get_active_client_manager()
    client = ClientRegistry.get_active_client()
    client_info = ClientRegistry.get_client_info(client)
    client_name = client_info.get("name", client)

    # Check if client is supported
    if client_manager is None:
        console.print("[bold red]Error:[/] Unsupported active client")
        console.print("Please switch to a supported client using 'mcpm client <client-name>'")
        return

    # Check if the server exists in the active client
    server_info = client_manager.get_server(server)
    if server_info is None:
        console.print(f"[bold red]Error:[/] Server '{server}' not found in {client_name}.")
        return

    # Get profile
    profile_info = profile_manager.get_profile(profile)
    if profile_info is None:
        console.print(f"[bold red]Error:[/] Profile '{profile}' not found.")
        return

    # Save profile
    profile_manager.set_profile(profile, server_info)
    console.print(f"\n[green]Server '{server}' applied to profile '{profile}' successfully.[/]\n")


@click.command()
@click.argument("profile_name")
def delete(profile_name):
    """Delete an MCPM profile."""
    if not profile_manager.delete_profile(profile_name):
        console.print(f"[bold red]Error:[/] Profile '{profile_name}' not found.")
        return
    console.print(f"\n[green]Profile '{profile_name}' deleted successfully.[/]\n")


@click.command()
@click.argument("profile_name")
def rename(profile_name):
    """Rename an MCPM profile."""
    new_profile_name = click.prompt("Enter new profile name", type=str)
    if profile_manager.get_profile(new_profile_name) is not None:
        console.print(f"[bold red]Error:[/] Profile '{new_profile_name}' already exists.")
        return
    if not profile_manager.rename_profile(profile_name, new_profile_name):
        console.print(f"[bold red]Error:[/] Profile '{profile_name}' not found.")
        return
    console.print(f"\n[green]Profile '{profile_name}' renamed to '{new_profile_name}' successfully.[/]\n")


@click.command()
@click.argument("profile")
@click.option("--server", "-s", required=True, help="Server to remove from profile")
def remove_server(server, profile):
    """Remove a server from an MCPM profile."""
    if not profile_manager.remove_server(server, profile):
        console.print(f"[bold red]Error:[/] Server '{server}' not found in profile '{profile}'.")
        return
    console.print(f"\n[green]Server '{server}' removed from profile '{profile}' successfully.[/]\n")


@click.command()
@click.argument("profile")
def show(profile):
    """Show the servers in an MCPM profile."""
    profile_info = profile_manager.get_profile(profile)
    if profile_info is None:
        console.print(f"[bold red]Error:[/] Profile '{profile}' not found.")
        return
    console.print(f"\n[green]Profile '{profile}' contains the following servers:[/]\n")
    for server in profile_info:
        console.print(f"[bold cyan]{server.name}[/]")
        command = server.command
        console.print(f"  Command: [green]{command}[/]")

        # Display arguments
        args = server.args
        if args:
            console.print("  Arguments:")
            for i, arg in enumerate(args):
                console.print(f"    {i}: [yellow]{escape(arg)}[/]")

        # Display environment variables
        env_vars = server.env
        if env_vars:
            console.print("  Environment Variables:")
            for key, value in env_vars.items():
                console.print(f'    [bold blue]{key}[/] = [green]"{value}"[/]')
        else:
            console.print("  Environment Variables: [italic]None[/]")

        # Add a separator line between servers
        console.print("  " + "-" * 50)
    console.print("\n")


# Register all commands with the profile group
profile.add_command(list)
profile.add_command(add)
profile.add_command(show)
profile.add_command(apply)
profile.add_command(delete)
profile.add_command(rename)
profile.add_command(remove_server, name="rm-server")
