"""Profile list command."""

from rich.console import Console
from rich.table import Table

from mcpm.core.schema import CustomServerConfig, STDIOServerConfig
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.rich_click_config import click

console = Console()
profile_config_manager = ProfileConfigManager()


@click.command(name="ls")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed server information")
@click.help_option("-h", "--help")
def list_profiles(verbose=False):
    """List all MCPM profiles."""
    profiles = profile_config_manager.list_profiles()
    if not profiles:
        console.print("\\n[yellow]No profiles found.[/]\\n")
        return
    console.print(f"\\n[green]Found {len(profiles)} profile(s)[/]\\n")
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
            row.append("\\n".join(details))
        table.add_row(*row)
    console.print(table)
