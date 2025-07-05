from rich.console import Console

from mcpm.clients.client_registry import ClientRegistry
from mcpm.core.schema import ServerConfig, STDIOServerConfig
from mcpm.global_config import GlobalConfigManager
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.config import NODE_EXECUTABLES, ConfigManager
from mcpm.utils.scope import ScopeType, parse_server

console = Console()
global_config_manager = GlobalConfigManager()


def determine_scope(scope: str | None) -> tuple[ScopeType | None, str | None]:
    """v2.0: This function is deprecated. All operations use global configuration.

    This is kept for backwards compatibility but always returns global scope.
    """
    # v2.0: Everything uses global configuration - no scope needed
    # Return a special marker to indicate global scope
    return ScopeType.GLOBAL, "global"


def determine_target(target: str) -> tuple[ScopeType | None, str | None, str | None]:
    """v2.0: Parse target but always use global scope for servers."""
    scope_type, scope, server_name = parse_server(target)

    # In v2.0, if no scope is specified, default to global
    if not scope and server_name:
        return ScopeType.GLOBAL, "global", server_name

    # If scope is specified but we're looking for a server, it might be a profile operation
    if scope and server_name:
        return scope_type, scope, server_name

    # If no server name, this might be a profile-only operation
    if scope and not server_name:
        return scope_type, scope, ""

    return None, None, None


# v2.0 Global server management functions


def global_add_server(server_config: ServerConfig, force: bool = False) -> bool:
    """Add a server to the global MCPM configuration."""
    if global_config_manager.server_exists(server_config.name) and not force:
        console.print(f"[bold red]Error:[/] Server '{server_config.name}' already exists in global configuration.")
        console.print("Use --force to override.")
        return False

    server_config = _replace_node_executable(server_config)
    return global_config_manager.add_server(server_config, force)


def global_remove_server(server_name: str) -> bool:
    """Remove a server from the global MCPM configuration and clean up profile tags."""
    if not global_config_manager.server_exists(server_name):
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in global configuration.")
        return False

    # Remove from global config (this automatically removes all profile tags)
    success = global_config_manager.remove_server(server_name)

    # No need for additional profile cleanup since virtual profiles
    # are managed automatically through profile tags on servers

    return success


def global_get_server(server_name: str) -> ServerConfig | None:
    """Get a server from the global MCPM configuration."""
    server = global_config_manager.get_server(server_name)
    if not server:
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in global configuration.")
    return server


def global_list_servers() -> dict[str, ServerConfig]:
    """List all servers in the global MCPM configuration."""
    return global_config_manager.list_servers()


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
