import shlex

import click
from rich.console import Console
from rich.prompt import Confirm, Prompt

from mcpm.commands.target_operations.common import client_add_server, determine_scope, profile_add_server
from mcpm.core.schema import RemoteServerConfig, STDIOServerConfig
from mcpm.utils.display import print_server_config
from mcpm.utils.scope import ScopeType

console = Console()


@click.group()
@click.help_option("-h", "--help")
def import_server():
    """Add server definitions manually."""
    pass


@import_server.command()
@click.argument("server_name", required=True)
@click.option("--command", "-c", help="Executable command", required=True)
@click.option("--args", "-a", multiple=True, help="Arguments for the command (can be used multiple times)")
@click.option("--env", "-e", multiple=True, help="Environment variables, format: ENV=val (can be used multiple times)")
@click.option("--target", "-t", help="Target client or profile")
@click.option("--force", is_flag=True, help="Force reinstall if server is already installed")
@click.help_option("-h", "--help")
def stdio(server_name, command, args, env, target, force):
    """Add a server by specifying command, args, and env variables.
    Examples:

    \b
        mcpm import stdio <server_name> --command <command> --args <arg1> --args <arg2> --env <var1>=<value1> --env <var2>=<value2>
    """
    scope_type, scope = determine_scope(target)
    if not scope:
        return

    # Extract env variables
    env_vars = {}
    for item in env:
        if "=" in item:
            key, value = item.split("=", 1)
            env_vars[key] = value
        else:
            console.print(f"[yellow]Ignoring invalid env: {item}[/]")

    try:
        # support spaces and quotes in args
        parsed_args = shlex.split(" ".join(args)) if args else []
        server_config = STDIOServerConfig(
            name=server_name,
            command=command,
            args=parsed_args,
            env=env_vars,
        )
        print_server_config(server_config)
    except ValueError as e:
        console.print(f"[bold red]Error:[/] {e}")
        return

    if not Confirm.ask(f"Add this server to {scope_type} {scope}?"):
        return
    console.print(f"[green]Importing server to {scope_type} {scope}[/]")

    if scope_type == ScopeType.CLIENT:
        success = client_add_server(scope, server_config, force)
    else:
        success = profile_add_server(scope, server_config, force)

    if success:
        console.print(f"[bold green]Stdio server '{server_name}' added successfully to {scope_type} {scope}.")
    else:
        console.print(f"[bold red]Failed to add stdio server '{server_name}' to {scope_type} {scope}.")


@import_server.command()
@click.argument("server_name", required=True)
@click.option("--url", "-u", required=True, help="Server URL")
@click.option("--header", "-H", multiple=True, help="HTTP headers, format: KEY=val (can be used multiple times)")
@click.option("--target", "-t", help="Target to import server to")
@click.option("--force", is_flag=True, help="Force reinstall if server is already installed")
@click.help_option("-h", "--help")
def remote(server_name, url, header, target, force):
    """Add a server by specifying a URL and headers.
    Examples:

    \b
        mcpm import remote <server_name> --url <url> --header <key1>=<value1> --header <key2>=<value2>
    """
    scope_type, scope = determine_scope(target)
    if not scope:
        return

    headers = {}
    for item in header:
        if "=" in item:
            key, value = item.split("=", 1)
            headers[key] = value
        else:
            console.print(f"[yellow]Ignoring invalid header: {item}[/]")

    try:
        server_config = RemoteServerConfig(
            name=server_name,
            url=url,
            headers=headers,
        )
        print_server_config(server_config)
    except ValueError as e:
        console.print(f"[bold red]Error:[/] {e}")
        return

    if not Confirm.ask(f"Add this server to {scope_type} {scope}?"):
        return
    console.print(f"[green]Importing server to {scope_type} {scope}[/]")

    if scope_type == ScopeType.CLIENT:
        success = client_add_server(scope, server_config, force)
    else:
        success = profile_add_server(scope, server_config, force)

    if success:
        console.print(f"[bold green]Remote server '{server_name}' added successfully to {scope_type} {scope}.")
    else:
        console.print(f"[bold red]Failed to add remote server '{server_name}' to {scope_type} {scope}.")


@import_server.command()
@click.option("--target", "-t", help="Target to import server to")
@click.help_option("-h", "--help")
def interact(target: str | None = None):
    """Add a server by manually configuring it interactively."""
    scope_type, scope = determine_scope(target)
    if not scope:
        return

    server_name = Prompt.ask("Enter server name")
    if not server_name:
        console.print("[red]Server name cannot be empty.[/]")
        return

    config_type = Prompt.ask("Select server type", choices=["stdio", "remote"], default="stdio")

    if config_type == "stdio":
        command = Prompt.ask("Enter command (executable)")
        args = Prompt.ask("Enter arguments (space-separated, optional)", default="")
        env_input = Prompt.ask("Enter env variables (format: KEY=VAL, comma-separated, optional)", default="")
        env = {}
        if env_input.strip():
            for pair in env_input.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    env[k.strip()] = v.strip()
        try:
            # support spaces and quotes in args
            parsed_args = shlex.split(args) if args.strip() else []
            server_config = STDIOServerConfig(
                name=server_name,
                command=command,
                args=parsed_args,
                env=env,
            )
        except ValueError as e:
            console.print(f"[bold red]Error:[/] {e}")
            return
    elif config_type == "remote":
        url = Prompt.ask("Enter remote server URL")
        headers_input = Prompt.ask("Enter HTTP headers (format: KEY=VAL, comma-separated, optional)", default="")
        headers = {}
        if headers_input.strip():
            for pair in headers_input.split(","):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    headers[k.strip()] = v.strip()
        try:
            server_config = RemoteServerConfig(
                name=server_name,
                url=url,
                headers=headers,
            )
        except ValueError as e:
            console.print(f"[bold red]Error:[/] {e}")
            return
    else:
        console.print(f"[red]Unknown server type: {config_type}[/]")
        return

    print_server_config(server_config)
    if not Confirm.ask(f"Add this server to {scope_type} {scope}?"):
        return
    console.print(f"[green]Importing server to {scope_type} {scope}[/]")

    if scope_type == ScopeType.CLIENT:
        success = client_add_server(scope, server_config, False)
    else:
        success = profile_add_server(scope, server_config, False)

    if success:
        console.print(
            f"[bold green]{config_type.upper()} server '{server_name}' added successfully to {scope_type} {scope}."
        )
    else:
        console.print(f"[bold red]Failed to add {config_type.upper()} server '{server_name}' to {scope_type} {scope}.")
