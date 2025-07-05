"""Migrate command for MCPM - Manual v1 to v2 migration"""

from rich.console import Console

from mcpm.migration import V1ConfigDetector, V1ToV2Migrator
from mcpm.utils.rich_click_config import click

console = Console()


@click.command()
@click.option("--force", is_flag=True, help="Force migration even if v1 config not detected")
@click.help_option("-h", "--help")
def migrate(force):
    """Migrate v1 configuration to v2.

    This command helps you migrate from MCPM v1 to v2, converting your
    profiles, servers, and configuration to the new simplified format.

    Examples:
        mcpm migrate              # Check for v1 config and migrate if found
        mcpm migrate --force      # Force migration check
    """
    detector = V1ConfigDetector()

    if not force and not detector.has_v1_config():
        console.print("[yellow]No v1 configuration detected.[/]")
        console.print("If you believe this is incorrect, use [cyan]--force[/] to run migration anyway.")
        console.print("\nTo learn about v2 features, run: [cyan]mcpm --help[/]")
        return

    migrator = V1ToV2Migrator()

    choice = migrator.show_migration_prompt()
    if choice == "migrate":
        success = migrator.migrate_config()
        if success:
            console.print("\n[bold green]🎉 Migration completed successfully![/]")
            console.print("You can now use all v2 features. Run [cyan]mcpm ls[/] to see your servers.")
        else:
            console.print("\n[red]❌ Migration failed. Check the output above for details.[/]")
    elif choice == "start_fresh":
        success = migrator.start_fresh()
        if success:
            console.print("\n[bold green]🎉 Fresh start completed successfully![/]")
            console.print("You can now start building your v2 configuration from scratch.")
        else:
            console.print("\n[red]❌ Fresh start failed. Check the output above for details.[/]")
    else:
        console.print("\n[yellow]Migration cancelled.[/]")
        console.print("You can run [cyan]mcpm migrate[/] again anytime to migrate your configuration.")
