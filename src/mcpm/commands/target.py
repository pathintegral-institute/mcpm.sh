import click
from rich.console import Console
from rich.panel import Panel

from mcpm.clients.client_registry import ClientRegistry
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.scope import ScopeType, extract_from_scope, format_scope

console = Console()


@click.group()
@click.help_option("-h", "--help")
def target():
    """Manage MCPM working target."""
    pass


@target.command(name="set", context_settings=dict(help_option_names=["-h", "--help"]))
@click.argument("target", required=True)
def set_target(target):
    """Set the active MCPM working target.

    TARGET is the name of the client or profile to set as active.
    Examples:

    \b
        mcpm target set @windsurf
        mcpm target set %profile_dev
    """

    scope_type, scope = extract_from_scope(target)
    if not scope:
        console.print(f"[bold red]Error:[/] Invalid target: {target}")
        return
    scope_name = format_scope(scope_type, scope)
    # Set the active target
    if scope_name == ClientRegistry.get_active_target():
        console.print(f"[bold yellow]Note:[/] {target} is already the active target")
        return

    success = False
    if scope_type == ScopeType.CLIENT:
        # Get the list of supported clients
        supported_clients = ClientRegistry.get_supported_clients()

        # Set the active client if provided
        if scope not in supported_clients:
            console.print(f"[bold red]Error:[/] Unknown client: {scope}")
            console.print(f"Supported clients: {', '.join(sorted(supported_clients))}")
            return

        # Attempt to set the active client with active profile inner switched
        success = ClientRegistry.set_active_target(scope_name)
        if success:
            console.print(f"[bold green]Success:[/] Active client set to {scope}")
    else:
        # Set the active profile
        profiles = ProfileConfigManager().list_profiles()
        if scope not in profiles:
            console.print(f"[bold red]Error:[/] Unknown profile: {scope}")
            console.print(f"Available profiles: {', '.join(sorted(profiles.keys()))}")
            return

        # Attempt to set the active profile with active client inner switched
        success = ClientRegistry.set_active_target(scope_name)
        if success:
            console.print(f"[bold green]Success:[/] Active profile set to {scope}")

    if success:
        # Provide information about what this means
        panel = Panel(
            f"The active target ({scope_name}) will be used for all MCP operations.\n"
            f"Commands like 'mcpm ls', 'mcpm add', 'mcpm rm', 'mcpm stash', and 'mcpm pop' will now operate on {scope_name}.",
            title="Active Target Changed",
            border_style="green",
        )
        console.print(panel)
    else:
        console.print(f"[bold red]Error:[/] Failed to set {target} as the active target")
