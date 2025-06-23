import click
from rich.console import Console
from rich.table import Table

from mcpm.clients.client_registry import ClientRegistry
from mcpm.core.schema import CustomServerConfig, STDIOServerConfig
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.config import ConfigManager

profile_config_manager = ProfileConfigManager()
console = Console()


@click.group()
@click.help_option("-h", "--help")
def profile():
    """Manage MCPM profiles."""
    pass


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
                elif isinstance(config, CustomServerConfig):
                    details.append(f"{config.name}: Custom")
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
            profile_server = client_manager.get_server(profile_name)
            if profile_server:
                # Deactivate the profile in this client
                client_manager.deactivate_profile(profile_name)
                console.print(f"\n[green]Profile '{profile_name}' removed successfully from client '{client}'.[/]\n")

    # fresh the active_profile
    activated_profile = ClientRegistry.get_active_profile()
    if activated_profile == profile_name:
        ClientRegistry.set_active_target(None)

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
            profile_server = client_manager.get_server(profile_name)
            if profile_server:
                # fresh the config
                client_manager.deactivate_profile(profile_name)
                client_manager.activate_profile(new_profile_name, config_manager.get_router_config())
                console.print(f"\n[green]Profile '{profile_name}' replaced successfully in client '{client}'.[/]\n")

    # fresh the active_profile
    activated_profile = ClientRegistry.get_active_profile()
    if activated_profile == profile_name:
        ClientRegistry.set_active_target(new_profile_name)

    console.print(f"\n[green]Profile '{profile_name}' renamed to '{new_profile_name}' successfully.[/]\n")
