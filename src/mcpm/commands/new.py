"""
New command - Create new server configurations with interactive and non-interactive modes
"""

import sys
from typing import Optional

from rich.console import Console

from mcpm.commands.edit import _create_new_server
from mcpm.core.schema import RemoteServerConfig, STDIOServerConfig
from mcpm.global_config import GlobalConfigManager
from mcpm.utils.display import print_error
from mcpm.utils.non_interactive import (
    create_server_config_from_params,
    is_non_interactive,
    should_force_operation,
)
from mcpm.utils.rich_click_config import click

console = Console()
global_config_manager = GlobalConfigManager()


@click.command(name="new", context_settings=dict(help_option_names=["-h", "--help"]))
@click.argument("server_name", required=False)
@click.option("--type", "server_type", type=click.Choice(["stdio", "remote"]), help="Server type")
@click.option("--command", help="Command to execute (required for stdio servers)")
@click.option("--args", help="Command arguments (space-separated)")
@click.option("--env", help="Environment variables (KEY1=value1,KEY2=value2)")
@click.option("--url", help="Server URL (required for remote servers)")
@click.option("--headers", help="HTTP headers (KEY1=value1,KEY2=value2)")
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
def new(
    server_name: Optional[str],
    server_type: Optional[str],
    command: Optional[str],
    args: Optional[str],
    env: Optional[str],
    url: Optional[str],
    headers: Optional[str],
    force: bool,
):
    """Create a new server configuration.

    Interactive by default, or use CLI parameters for automation.
    Set MCPM_NON_INTERACTIVE=true to disable prompts.
    """
    # Check if we have enough parameters for non-interactive mode
    has_cli_params = bool(server_name and server_type)
    force_non_interactive = is_non_interactive() or should_force_operation() or force

    if has_cli_params or force_non_interactive:
        exit_code = _create_new_server_non_interactive(
            server_name=server_name,
            server_type=server_type,
            command=command,
            args=args,
            env=env,
            url=url,
            headers=headers,
            force=force,
        )
        sys.exit(exit_code)
    else:
        # Fall back to interactive mode
        return _create_new_server()


def _create_new_server_non_interactive(
    server_name: Optional[str],
    server_type: Optional[str],
    command: Optional[str],
    args: Optional[str],
    env: Optional[str],
    url: Optional[str],
    headers: Optional[str],
    force: bool,
) -> int:
    """Create a new server configuration non-interactively."""
    try:
        # Validate required parameters
        if not server_name:
            print_error("Server name is required", "Use: mcpm new <server_name> --type <stdio|remote>")
            return 1

        if not server_type:
            print_error("Server type is required", "Use: --type stdio or --type remote")
            return 1

        # Check if server already exists
        if global_config_manager.get_server(server_name):
            if not force and not should_force_operation():
                print_error(
                    f"Server '{server_name}' already exists", "Use --force to overwrite or choose a different name"
                )
                return 1
            console.print(f"[yellow]Overwriting existing server '{server_name}'[/]")

        # Create server configuration from parameters
        config_dict = create_server_config_from_params(
            name=server_name,
            server_type=server_type,
            command=command,
            args=args,
            env=env,
            url=url,
            headers=headers,
        )

        # Create the appropriate server config object
        if server_type == "stdio":
            server_config = STDIOServerConfig(
                name=config_dict["name"],
                command=config_dict["command"],
                args=config_dict.get("args", []),
                env=config_dict.get("env", {}),
            )
        else:  # remote
            server_config = RemoteServerConfig(
                name=config_dict["name"],
                url=config_dict["url"],
                headers=config_dict.get("headers", {}),
            )

        # Display configuration summary
        console.print(f"\n[bold green]Creating server '{server_name}':[/]")
        console.print(f"Type: [cyan]{server_type.upper()}[/]")

        if server_type == "stdio":
            console.print(f"Command: [cyan]{server_config.command}[/]")
            if server_config.args:
                console.print(f"Arguments: [cyan]{' '.join(server_config.args)}[/]")
        else:  # remote
            console.print(f"URL: [cyan]{server_config.url}[/]")
            if server_config.headers:
                headers_str = ", ".join(f"{k}={v}" for k, v in server_config.headers.items())
                console.print(f"Headers: [cyan]{headers_str}[/]")

        if hasattr(server_config, "env") and server_config.env:
            env_str = ", ".join(f"{k}={v}" for k, v in server_config.env.items())
            console.print(f"Environment: [cyan]{env_str}[/]")

        # Save the server
        global_config_manager.add_server(server_config, force=force)
        console.print(f"[green]✅ Successfully created server '[cyan]{server_name}[/]'[/]")

        return 0

    except ValueError as e:
        print_error("Invalid parameter", str(e))
        return 1
    except Exception as e:
        print_error("Failed to create server", str(e))
        return 1
