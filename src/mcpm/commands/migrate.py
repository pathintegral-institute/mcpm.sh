"""Migrate command for MCPM - Migration utilities"""

from rich.console import Console

from mcpm.migration.transport_migrator import TransportMigrator
from mcpm.utils.rich_click_config import click

console = Console()


@click.command()
@click.option("--force", is_flag=True, help="Force migration checks")
@click.help_option("-h", "--help")
def migrate(force):
    """Migrate configuration to latest standards.

    Current migrations:
    - SSE to Streamable HTTP transport (v4.0 -> v4.1)

    Examples:
        mcpm migrate              # Run all active migrations
    """
    console.print("[bold blue]Starting MCPM migration...[/]")

    # 1. Transport Migration (SSE -> HTTP)
    migrator = TransportMigrator()
    if migrator.migrate_all_clients():
        console.print("\n[bold green]✅ Transport migration completed successfully![/]")
    else:
        console.print("\n[green]Transport configuration is already up to date.[/]")

    console.print("\n[dim]Migration check complete.[/]")
