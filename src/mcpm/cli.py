"""MCPM CLI - Main entry point for the Model Context Protocol Manager CLI."""

from __future__ import annotations

# Import rich-click configuration before anything else
import os
from collections import OrderedDict
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, NamedTuple

from rich.console import Console
from rich.traceback import Traceback
from rich.traceback import install as install_rich_traceback

from mcpm.clients.client_config import ClientConfigManager
from mcpm.utils.logging_config import setup_logging
from mcpm.utils.rich_click_config import click, get_header_text

console = Console()  # stdout for regular CLI output
err_console = Console(stderr=True)  # stderr for errors/tracebacks
client_config_manager = ClientConfigManager()

# Setup Rich logging early - this runs when the module is imported
setup_logging()

# Install Rich's global exception handler to use stderr instead of stdout
# This prevents Rich/rich-gradient from routing tracebacks to stdout
install_rich_traceback(console=err_console, show_locals=True)

# Custom context settings to handle main command help specially
CONTEXT_SETTINGS: Dict[str, Any] = dict(help_option_names=[])


def print_logo():
    """Print an elegant gradient logo with invisible Panel for width control"""
    console.print(get_header_text())


def handle_exceptions(func):
    """Decorator to catch unhandled exceptions and provide a helpful error message."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            err_console.print(Traceback(show_locals=True))
            err_console.print("[bold red]An unexpected error occurred.[/bold red]")
            err_console.print(
                "Please report this issue on our GitHub repository: "
                "[link=https://github.com/pathintegral-institute/mcpm.sh/issues]https://github.com/pathintegral-institute/mcpm.sh/issues[/link]"
            )

    return wrapper

class CommandSpec(NamedTuple):
    module: str
    attribute: str
    hidden: bool = False


class LazyCommandGroup(click.Group):
    """Click group that imports commands on demand to avoid import side effects."""

    def __init__(self, *args, command_specs: Dict[str, CommandSpec], **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Preserve insertion order for predictable help output
        self._command_specs: OrderedDict[str, CommandSpec] = OrderedDict(command_specs)
        self._command_cache: Dict[str, click.Command] = {}

    def list_commands(self, ctx: click.Context) -> list[str]:
        # Use insertion order (no sorting) to match the curated help layout
        visible_commands = [
            name for name, spec in self._command_specs.items() if not spec.hidden
        ]
        return visible_commands + super().list_commands(ctx)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        if cmd_name in self._command_cache:
            return self._command_cache[cmd_name]

        spec = self._command_specs.get(cmd_name)
        if spec is None:
            return super().get_command(ctx, cmd_name)

        module = import_module(spec.module)
        command: click.Command = getattr(module, spec.attribute)

        self._command_cache[cmd_name] = command
        return command


COMMAND_SPECS: OrderedDict[str, CommandSpec] = OrderedDict(
    [
        ("search", CommandSpec("mcpm.commands.search", "search")),
        ("info", CommandSpec("mcpm.commands.info", "info")),
        ("list", CommandSpec("mcpm.commands.list", "list")),
        ("ls", CommandSpec("mcpm.commands.list", "list", hidden=True)),
        ("install", CommandSpec("mcpm.commands.install", "install")),
        ("uninstall", CommandSpec("mcpm.commands.uninstall", "uninstall")),
        ("edit", CommandSpec("mcpm.commands.edit", "edit")),
        ("new", CommandSpec("mcpm.commands.new", "new")),
        ("run", CommandSpec("mcpm.commands.run", "run")),
        ("inspect", CommandSpec("mcpm.commands.inspect", "inspect")),
        ("profile", CommandSpec("mcpm.commands.profile", "profile")),
        ("doctor", CommandSpec("mcpm.commands.doctor", "doctor")),
        ("usage", CommandSpec("mcpm.commands.usage", "usage")),
        ("config", CommandSpec("mcpm.commands.config", "config")),
        ("migrate", CommandSpec("mcpm.commands.migrate", "migrate")),
        ("share", CommandSpec("mcpm.commands.share", "share")),
        ("client", CommandSpec("mcpm.commands.client", "client")),
    ]
)


@click.group(
    name="mcpm",
    cls=LazyCommandGroup,
    command_specs=COMMAND_SPECS,
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

    try:
        # Check if the current working directory is valid.
        os.getcwd()
    except OSError:
        # If getcwd() fails, it means the directory doesn't exist.
        # This can happen when mcpm is called from certain environments
        # like some Electron apps that don't set a valid cwd.
        home_dir = str(Path.home())
        err_console.print(
            f"Current working directory is invalid. Changing to home directory: {home_dir}",
            style="bold yellow"
        )
        os.chdir(home_dir)

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
        return

    # If no command was invoked, show help with header and footer
    if ctx.invoked_subcommand is None:
        console.print(get_header_text())
        # Temporarily disable global footer to avoid duplication
        original_footer = click.rich_click.FOOTER_TEXT
        click.rich_click.FOOTER_TEXT = None
        click.echo(ctx.get_help())
        click.rich_click.FOOTER_TEXT = original_footer

if __name__ == "__main__":
    main()
