"""
MCPM CLI - Main entry point for the Model Context Protocol Manager CLI
"""

# Import rich-click configuration before anything else
from rich.console import Console
from rich.traceback import Traceback

from mcpm import __version__
from mcpm.clients.client_config import ClientConfigManager
from mcpm.commands import (
    add,
    client,
    config,
    doctor,
    edit,
    info,
    inspect,
    list,
    migrate,
    profile,
    remove,
    run,
    search,
    usage,
)
from mcpm.commands.share import share
from mcpm.migration import V1ConfigDetector, V1ToV2Migrator
from mcpm.utils.logging_config import setup_logging
from mcpm.utils.rich_click_config import click, get_header_text, get_footer_text

console = Console()
client_config_manager = ClientConfigManager()

# Setup Rich logging early - this runs when the module is imported
setup_logging()

# Custom context settings to handle main command help specially
CONTEXT_SETTINGS = dict(help_option_names=[])


def print_logo():
    """Print an elegant gradient logo with invisible Panel for width control"""
    from rich import box
    from rich.console import Group
    from rich.panel import Panel
    from rich.text import Text
    from rich_gradient import Gradient

    # Clean ASCII art design - simplified with light shades
    logo_text = """
 ███░   ███░  ██████░ ██████░ ███░   ███░
 ████░ ████░ ██░░░░░░ ██░░░██░████░ ████░
 ██░████░██░ ██░      ██████░░██░████░██░
 ██░░██░░██░ ██░      ██░░░░░ ██░░██░░██░
 ██░ ░░░ ██░ ░██████░ ██░     ██░ ░░░ ██░
 ░░░     ░░░  ░░░░░░░ ░░░     ░░░     ░░░

"""

    # Purple-to-pink gradient palette
    primary_colors = ["#8F87F1", "#C68EFD", "#E9A5F1", "#FED2E2"]
    accent_colors = ["#3B82F6", "#EF4444"]  # Blue to red
    warm_colors = ["#10B981", "#F59E0B"]  # Green to orange
    tagline_colors = ["#06B6D4", "#EF4444"]  # Cyan to red

    # Create gradient using rich-gradient with narrow console for better gradient distribution
    temp_console = Console(width=50)  # Close to ASCII art width
    logo_gradient_obj = Gradient(logo_text, colors=primary_colors)
    
    # Capture the rendered gradient
    with temp_console.capture() as capture:
        temp_console.print(logo_gradient_obj, justify="center")
    logo_gradient = Text.from_ansi(capture.get())

# Create solid color text for title and tagline - harmonized with gradient
    title_text = Text()
    title_text.append("Model Context Protocol Manager", style="#8F87F1 bold")
    title_text.append(" v", style="#C68EFD")
    title_text.append(__version__, style="#E9A5F1 bold")
    
    tagline_text = Text()
    tagline_text.append("Open Source with ", style="#FED2E2")
    tagline_text.append("♥", style="#E9A5F1")
    tagline_text.append(" by Path Integral Institute", style="#FED2E2")

    # Create content group with proper spacing - all left aligned for consistency
    content = Group(
        "",  # Empty line at top
        logo_gradient,
        "",
        title_text,
        "",
        tagline_text,
        "",  # Empty line at bottom
    )

    # Create invisible panel for width constraint only
    invisible_panel = Panel(
        content,
        width=120,
        box=box.SIMPLE,  # Simple box style
        border_style="dim",  # Very dim border
        padding=(0, 1),
    )

    console.print(invisible_panel)


def handle_exceptions(func):
    """Decorator to catch unhandled exceptions and provide a helpful error message."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            console.print(Traceback(show_locals=True))
            console.print("[bold red]An unexpected error occurred.[/bold red]")
            console.print(
                "Please report this issue on our GitHub repository: "
                "[link=https://github.com/pathintegral-institute/mcpm.sh/issues]https://github.com/pathintegral-institute/mcpm.sh/issues[/link]"
            )

    return wrapper


@click.group(
    name="mcpm",
    context_settings=CONTEXT_SETTINGS,
    invoke_without_command=True,
    help="""
Centralized MCP server management - discover, install, run, and share servers.

Manage servers globally, organize with profiles, monitor usage, and integrate 
with all MCP clients.
""",
)
@click.option("-v", "--version", is_flag=True, help="Show version and exit.")
@click.option("-h", "--help", "help_flag", is_flag=True, help="Show this message and exit.")
@click.pass_context
@handle_exceptions
def main(ctx, version, help_flag):
    """Main entry point for MCPM CLI."""
    if version:
        print_logo()
        return
    
    if help_flag:
        # Show custom help with header and footer for main command only
        console.print(get_header_text())
        # Temporarily disable global footer to avoid duplication
        original_footer = click.rich_click.FOOTER_TEXT
        click.rich_click.FOOTER_TEXT = None
        click.echo(ctx.get_help())
        click.rich_click.FOOTER_TEXT = original_footer
        console.print(get_footer_text())
        return

    # Check for v1 configuration and offer migration (even with subcommands)
    detector = V1ConfigDetector()
    if detector.has_v1_config():
        migrator = V1ToV2Migrator()
        migration_choice = migrator.show_migration_prompt()
        if migration_choice == "migrate":
            migrator.migrate_config()
            return
        elif migration_choice == "start_fresh":
            migrator.start_fresh()
            # Continue to execute the subcommand
        # If "ignore", continue to subcommand without migration

    # If no command was invoked, show help with header and footer
    if ctx.invoked_subcommand is None:
        console.print(get_header_text())
        # Temporarily disable global footer to avoid duplication
        original_footer = click.rich_click.FOOTER_TEXT
        click.rich_click.FOOTER_TEXT = None
        click.echo(ctx.get_help())
        click.rich_click.FOOTER_TEXT = original_footer
        console.print(get_footer_text())


# Register v2.0 commands
main.add_command(search.search)
main.add_command(info.info)
main.add_command(list.list, name="ls")
main.add_command(add.add, name="install")
main.add_command(remove.remove, name="uninstall")
main.add_command(edit.edit)
main.add_command(run.run)
main.add_command(inspect.inspect)
main.add_command(profile.profile, name="profile")
main.add_command(doctor.doctor)
main.add_command(usage.usage)
main.add_command(config.config)
main.add_command(migrate.migrate)
main.add_command(share)


# Keep these for now but they could be simplified later
main.add_command(client.client)

if __name__ == "__main__":
    main()
