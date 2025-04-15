from rich.console import Console

from mcpm.clients.client_registry import ClientRegistry
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.schemas.server_config import ServerConfig
from mcpm.utils.display import print_active_scope, print_no_active_scope
from mcpm.utils.scope import ScopeType, extract_from_scope, parse_server

console = Console()


def determine_target(target: str) -> tuple[ScopeType | None, str | None, str | None]:
    scope_type, scope, server_name = parse_server(target)
    if not scope:
        active_scope = ClientRegistry.determine_active_scope()
        if not active_scope:
            print_no_active_scope()
            return None, None, None
        scope_type, scope = extract_from_scope(active_scope)
        print_active_scope(active_scope)
    return scope_type, scope, server_name


def client_add_server(client: str, server_config: ServerConfig, force: bool = False) -> bool:
    client_manager = ClientRegistry.get_client_manager(client)
    if not client_manager:
        console.print(f"[bold red]Error:[/] Client '{client}' not found.")
        return False
    if client_manager.get_server(server_config.name) and not force:
        console.print(f"[bold red]Error:[/] Server '{server_config.name}' already exists in {client}.")
        console.print("Use --force to override.")
        return False
    success = client_manager.add_server(server_config)

    return success


def client_remove_server(client: str, server: str) -> bool:
    client_manager = ClientRegistry.get_client_manager(client)
    if not client_manager:
        console.print(f"[bold red]Error:[/] Client '{client}' not found.")
        return False
    success = client_manager.remove_server(server)
    return success


def client_get_server(client: str, server: str) -> ServerConfig | None:
    client_manager = ClientRegistry.get_client_manager(client)
    if not client_manager:
        console.print(f"[bold red]Error:[/] Client '{client}' not found.")
        return None
    return client_manager.get_server(server)


def profile_add_server(profile: str, server_config: ServerConfig, force: bool = False) -> bool:
    profile_manager = ProfileConfigManager()
    if profile_manager.get_profile(profile) is None:
        console.print(f"[bold red]Error:[/] Profile '{profile}' not found.")
        return False

    if profile_manager.get_profile_server(profile, server_config.name) and not force:
        console.print(f"[bold red]Error:[/] Server '{server_config.name}' already exists in {profile}.")
        console.print("Use --force to override.")
        return False
    success = profile_manager.set_profile(profile, server_config)
    return success


def profile_remove_server(profile: str, server: str) -> bool:
    profile_manager = ProfileConfigManager()
    if profile_manager.get_profile(profile) is None:
        console.print(f"[bold red]Error:[/] Profile '{profile}' not found.")
        return False
    success = profile_manager.remove_server(profile, server)
    return success


def profile_get_server(profile: str, server: str) -> ServerConfig | None:
    profile_manager = ProfileConfigManager()
    if profile_manager.get_profile(profile) is None:
        console.print(f"[bold red]Error:[/] Profile '{profile}' not found.")
        return None
    return profile_manager.get_profile_server(profile, server)
