import click
from rich.console import Console
from rich.table import Table

from mcpm.clients.client_registry import ClientRegistry
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.schemas.server_config import STDIOServerConfig
from mcpm.utils.config import ConfigManager

profile_config_manager = ProfileConfigManager()
console = Console()


@click.group()
@click.help_option("-h", "--help")
def profile():
    """Manage MCPM profiles."""
    pass


@click.command()
@click.argument("profile_name")
@click.option("--client", "-c", help="Client of the profile")
@click.help_option("-h", "--help")
def activate(profile_name, client=None):
    """Activate a profile.

    Sets the specified profile as the active profile.
    """
    # Activate the specified profile
    if profile_config_manager.get_profile(profile_name) is None:
        console.print(f"[bold red]Error:[/] Profile '{profile_name}' not found.")
        return

    # Set the active profile
    client_registry = ClientRegistry()
    config_manager = ConfigManager()

    activate_this_client: bool = client is None

    if client:
        if client == ClientRegistry.get_active_client():
            activate_this_client = True

        console.print(f"[bold cyan]Activating profile '{profile_name}' in client '{client}'...[/]")
        client_manager = ClientRegistry.get_client_manager(client)
        if client_manager is None:
            console.print(f"[bold red]Error:[/] Client '{client}' not found.")
            return
        success = client_manager.activate_profile(profile_name, config_manager.get_router_config())
    else:
        client = ClientRegistry.get_active_client()
        if client is None:
            console.print("[bold yellow]No active client found.[/]\n")
            return
        console.print(f"[bold cyan]Activating profile '{profile_name}' in active client '{client}'...[/]")
        client_manager = ClientRegistry.get_client_manager(client)
        if client_manager is None:
            console.print(f"[bold red]Error:[/] Client '{client}' not found.")
            return
        success = client_manager.activate_profile(profile_name, config_manager.get_router_config())
    if success and activate_this_client:
        client_registry.set_active_profile(profile_name)
        console.print(f"\n[green]Profile '{profile_name}' activated successfully.[/]\n")
    elif success:
        console.print(f"\n[green]Profile '{profile_name}' activated successfully for client '{client}'.[/]\n")
    else:
        console.print(f"[bold red]Error:[/] Failed to activate profile '{profile_name}'.")


@click.command()
@click.option("--client", "-c", help="Client of the profile")
@click.help_option("-h", "--help")
def deactivate(client=None):
    """Deactivate a profile.

    Unsets the active profile.
    """
    deactivate_this_client: bool = client is None

    # Set the active profile
    active_profile = ClientRegistry.get_active_profile()
    if deactivate_this_client and active_profile is None:
        console.print("[bold yellow]No active profile found.[/]\n")
        return
    console.print(f"\n[green]Deactivating profile '{active_profile}'...[/]")
    client_registry = ClientRegistry()

    if client:
        if client == ClientRegistry.get_active_client():
            deactivate_this_client = True

        console.print(f"[bold cyan]Deactivating profile '{active_profile}' in client '{client}'...[/]")
        client_manager = ClientRegistry.get_client_manager(client)
        if client_manager is None:
            console.print(f"[bold red]Error:[/] Client '{client}' not found.")
            return
        success = client_manager.deactivate_profile()
    else:
        client = ClientRegistry.get_active_client()
        if client is None:
            console.print("[bold yellow]No active client found.[/]\n")
            return
        console.print(f"[bold cyan]Deactivating profile '{active_profile}' in active client '{client}'...[/]")
        client_manager = ClientRegistry.get_client_manager(client)
        if client_manager is None:
            console.print(f"[bold red]Error:[/] Client '{client}' not found.")
            return
        success = client_manager.deactivate_profile()
    if success and deactivate_this_client:
        client_registry.set_active_profile(None)
        console.print(f"\n[yellow]Profile '{active_profile}' deactivated successfully.[/]\n")
    elif success:
        console.print(f"\n[yellow]Profile '{active_profile}' deactivated successfully for client '{client}'.[/]\n")
    else:
        console.print(f"[bold red]Error:[/] Failed to deactivate profile '{active_profile}' in client '{client}'.")


@profile.command(name="ls")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed server information")
@click.help_option("-h", "--help")
def list(verbose=False):
    """List all MCPM profiles."""
    profiles = profile_config_manager.list_profiles()
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
                if isinstance(config, STDIOServerConfig):
                    details.append(f"{config.name}: {config.command} {' '.join(config.args)}")
                else:
                    details.append(f"{config.name}: {config.url}")
            row.append("\n".join(details))
        table.add_row(*row)
    console.print(table)


@profile.command()
@click.argument("profile")
@click.option("--force", is_flag=True, help="Force add even if profile already exists")
@click.help_option("-h", "--help")
def add(profile, force=False):
    """Add a new MCPM profile."""
    if profile_config_manager.get_profile(profile) is not None and not force:
        console.print(f"[bold red]Error:[/] Profile '{profile}' already exists.")
        console.print("Use '--force' to overwrite the existing profile.")
        return

    profile_config_manager.new_profile(profile)

    console.print(f"\n[green]Profile '{profile}' added successfully.[/]\n")
    console.print(f"You can now add servers to this profile with 'mcpm add --target %{profile} <server_name>'\n")
    console.print(
        f"Or apply existing config to this profile with 'mcpm profile apply {profile} --server <server_name>'\n"
    )


@profile.command()
@click.argument("profile")
@click.option("--server", "-s", required=True, help="Server to apply config to")
@click.help_option("-h", "--help")
def apply(profile, server):
    """Apply an existing MCPM config to a profile."""
    client_manager = ClientRegistry.get_active_client_manager()
    client = ClientRegistry.get_active_client()
    if client is None:
        console.print("[bold red]Error:[/] No active client found.")
        return
    client_info = ClientRegistry.get_client_info(client)
    client_name = client_info.get("name", client)

    # Check if client is supported
    if client_manager is None:
        console.print("[bold red]Error:[/] Unsupported active client")
        console.print("Please switch to a supported client using 'mcpm client set <client-name>'")
        return

    # Check if the server exists in the active client
    server_info = client_manager.get_server(server)
    if server_info is None:
        console.print(f"[bold red]Error:[/] Server '{server}' not found in {client_name}.")
        return

    # Get profile
    profile_info = profile_config_manager.get_profile(profile)
    if profile_info is None:
        console.print(f"[bold red]Error:[/] Profile '{profile}' not found.")
        return

    # Save profile
    profile_config_manager.set_profile(profile, server_info)
    console.print(f"\n[green]Server '{server}' applied to profile '{profile}' successfully.[/]\n")


@profile.command("rm")
@click.argument("profile_name")
@click.help_option("-h", "--help")
def remove(profile_name):
    """Delete an MCPM profile."""
    if not profile_config_manager.delete_profile(profile_name):
        console.print(f"[bold red]Error:[/] Profile '{profile_name}' not found.")
        return
    # Check whether any client is associated with the deleted profile
    clients = ClientRegistry.get_supported_clients()
    for client in clients:
        client_manager = ClientRegistry.get_client_manager(client)
        if client_manager:
            profile_this_client_associated = client_manager.get_associated_profile()
            if profile_this_client_associated == profile_name:
                # Deactivate the profile in this client
                client_manager.deactivate_profile()
                console.print(f"\n[green]Profile '{profile_name}' deactivated successfully for client '{client}'.[/]\n")

    # fresh the active_profile
    activated_profile = ClientRegistry.get_active_profile()
    if activated_profile == profile_name:
        ClientRegistry.set_active_profile(None)

    console.print(f"\n[green]Profile '{profile_name}' deleted successfully.[/]\n")


@profile.command()
@click.argument("profile_name")
@click.help_option("-h", "--help")
def rename(profile_name):
    """Rename an MCPM profile."""
    new_profile_name = click.prompt("Enter new profile name", type=str)
    if profile_config_manager.get_profile(new_profile_name) is not None:
        console.print(f"[bold red]Error:[/] Profile '{new_profile_name}' already exists.")
        return
    if not profile_config_manager.rename_profile(profile_name, new_profile_name):
        console.print(f"[bold red]Error:[/] Profile '{profile_name}' not found.")
        return
    # Check whether any client is associated with the profile to be renamed
    clients = ClientRegistry.get_supported_clients()
    config_manager = ConfigManager()
    for client in clients:
        client_manager = ClientRegistry.get_client_manager(client)
        if client_manager:
            profile_this_client_associated = client_manager.get_associated_profile()
            if profile_this_client_associated == profile_name:
                # fresh the config
                client_manager.deactivate_profile()
                client_manager.activate_profile(new_profile_name, config_manager.get_router_config())
                console.print(f"\n[green]Profile '{profile_name}' deactivated successfully for client '{client}'.[/]\n")

    # fresh the active_profile
    activated_profile = ClientRegistry.get_active_profile()
    if activated_profile == profile_name:
        ClientRegistry.set_active_profile(new_profile_name)

    console.print(f"\n[green]Profile '{profile_name}' renamed to '{new_profile_name}' successfully.[/]\n")
