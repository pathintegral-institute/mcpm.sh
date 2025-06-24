from rich.console import Console

from mcpm.clients.client_registry import ClientRegistry
from mcpm.core.schema import ServerConfig, STDIOServerConfig
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.config import NODE_EXECUTABLES, ConfigManager
from mcpm.utils.display import print_active_scope, print_no_active_scope
from mcpm.utils.scope import ScopeType, extract_from_scope, parse_server

console = Console()


def determine_scope(scope: str | None) -> tuple[ScopeType | None, str | None]:
    if not scope:
        # Get the active scope
        scope = ClientRegistry.get_active_target()
        if not scope:
            print_no_active_scope()
            return None, None
        print_active_scope(scope)

    scope_type, scope = extract_from_scope(scope)
    return scope_type, scope


def determine_target(target: str) -> tuple[ScopeType | None, str | None, str | None]:
    scope_type, scope, server_name = parse_server(target)
    if not scope:
        scope_type, scope = determine_scope(scope)
        if not scope:
            return None, None, None
    return scope_type, scope, server_name


def _replace_node_executable(server_config: ServerConfig) -> ServerConfig:
    if not isinstance(server_config, STDIOServerConfig):
        return server_config
    command = server_config.command.strip()
    if command not in NODE_EXECUTABLES:
        return server_config
    config = ConfigManager().get_config()
    config_node_executable = config.get("node_executable")
    if not config_node_executable:
        return server_config
    if config_node_executable != command:
        console.print(f"[bold cyan]Replace node executable {command} with {config_node_executable}[/]")
        server_config.command = config_node_executable
    return server_config


def client_add_server(client: str, server_config: ServerConfig, force: bool = False) -> bool:
    client_manager = ClientRegistry.get_client_manager(client)
    if not client_manager:
        console.print(f"[bold red]Error:[/] Client '{client}' not found.")
        return False
    if client_manager.get_server(server_config.name) and not force:
        console.print(f"[bold red]Error:[/] Server '{server_config.name}' already exists in {client}.")
        console.print("Use --force to override.")
        return False
    server_config = _replace_node_executable(server_config)
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
    server_config = _replace_node_executable(server_config)
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


def client_add_profile(profile_name: str, client: str, alias_name: str | None = None) -> bool:
    client_manager = ClientRegistry.get_client_manager(client)
    if not client_manager:
        console.print(f"[bold red]Error:[/] Client '{client}' not found.")
        return False
    router_config = ConfigManager().get_router_config()
    if not router_config:
        console.print("[bold red]Error:[/] Router config not found.")
        return False

    success = client_manager.activate_profile(profile_name, router_config, alias_name)
    return success
