"""
Add command for adding MCP servers directly to client configurations
"""

import json
import os
import re

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from mcpm.clients.client_registry import ClientRegistry
from mcpm.commands.server_operations.common import client_add_server, profile_add_server
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.schemas.full_server_config import FullServerConfig
from mcpm.utils.display import print_active_scope, print_no_active_scope
from mcpm.utils.repository import RepositoryManager
from mcpm.utils.scope import ScopeType, extract_from_scope

console = Console()
repo_manager = RepositoryManager()
profile_config_manager = ProfileConfigManager()


@click.command()
@click.argument("server_name")
@click.option("--force", is_flag=True, help="Force reinstall if server is already installed")
@click.option("--alias", help="Alias for the server", required=False)
@click.option("--target", "-t", help="Target to add server to", required=False)
def add(server_name, force=False, alias=None, target: str | None = None):
    """Add an MCP server to a client configuration.

    Examples:
        mcpm add time
        mcpm add everything --force
        mcpm add youtube --alias yt
        mcpm add youtube --target %myprofile
    """
    config_name = alias or server_name

    if target is None:
        # Get the active scope
        target = ClientRegistry.determine_active_scope()
        if not target:
            print_no_active_scope()
            return
        print_active_scope(target)

    scope_type, scope = extract_from_scope(target)
    if scope_type == ScopeType.PROFILE:
        # Get profile
        profile = scope
        console.print(f"[yellow]Adding server to profile: {profile}[/]")
        profile_info = profile_config_manager.get_profile(profile)
        if profile_info is None:
            console.print(f"[yellow]Profile '{profile}' not found. Create new profile? [bold]y/n[/]", end=" ")
            if not Confirm.ask():
                return
            profile_config_manager.new_profile(profile)
            console.print(f"[green]Profile '{profile}' added successfully.[/]\n")
            profile_info = []

        # Check if server already exists in client config
        for server in profile_info:
            if server.name == config_name and not force:
                console.print(f"[yellow]Server '{config_name}' is already added to {profile}.[/]")
                console.print("Use '--force' to overwrite the existing configuration.")
                return

        target_name = profile
    else:
        # Get client
        client = scope
        console.print(f"[yellow]Adding server to client: {client}[/]")
        client_info = ClientRegistry.get_client_info(client)
        if client_info is None:
            console.print(f"[bold red]Error:[/] Client '{client}' not found.")
            return

        # Check if server already exists in client config
        for server in client_info:
            if server == config_name and not force:
                console.print(f"[yellow]Server '{config_name}' is already added to {client}.[/]")
                console.print("Use '--force' to overwrite the existing configuration.")
                return

        target_name = client

    # Get server metadata from repository
    server_metadata = repo_manager.get_server_metadata(server_name)
    if not server_metadata:
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in registry.")
        console.print(f"Available servers: {', '.join(repo_manager._fetch_servers().keys())}")
        return

    # Display server information
    display_name = server_metadata.get("display_name", server_name)
    description = server_metadata.get("description", "No description available")
    author_info = server_metadata.get("author", {})

    console.print(f"\n[bold]{display_name}[/] ({server_name})")
    console.print(f"[dim]{description}[/]")

    if author_info:
        author_name = author_info.get("name", "Unknown")
        author_url = author_info.get("url", "")
        console.print(f"[dim]Author: {author_name} {author_url}[/]")

    # Confirm addition
    if not force and not Confirm.ask(f"Add this server to {target_name}{' as ' + alias if alias else ''}?"):
        console.print("[yellow]Operation cancelled.[/]")
        return

    # Create server directory in the MCP directory
    base_dir = os.path.expanduser("~/.mcpm")
    os.makedirs(base_dir, exist_ok=True)

    servers_dir = os.path.join(base_dir, "servers")
    os.makedirs(servers_dir, exist_ok=True)

    server_dir = os.path.join(servers_dir, server_name)
    os.makedirs(server_dir, exist_ok=True)

    # Extract installation information
    installations = server_metadata.get("installations", {})

    # If no installation information is available, create minimal default values
    # This allows us to add the server config without full installation details
    installation_method = "manual"  # Single consolidated concept
    install_command = "echo"
    install_args = [f"Server {server_name} added to configuration"]
    package_name = None
    env_vars = {}
    required_args = {}

    # Process installation information if available
    selected_method = None  # Initialize selected_method to None to avoid UnboundLocalError
    if installations:
        # Find recommended installation method or default to the first one
        method_id = "default"  # ID of the method in the config

        # First check for a recommended method
        for key, method in installations.items():
            if method.get("recommended", False):
                selected_method = method
                method_id = key
                break

        # If no recommended method found, use the first one
        if not selected_method and installations:
            method_id = next(iter(installations))
            selected_method = installations[method_id]

        # If multiple methods are available and not forced, offer selection
        if len(installations) > 1 and not force:
            console.print("\n[bold]Available installation methods:[/]")
            methods_list = []

            for i, (key, method) in enumerate(installations.items(), 1):
                method_type = method.get("type", "unknown")
                description = method.get("description", f"{method_type} installation")
                recommended = " [green](recommended)[/]" if method.get("recommended", False) else ""

                console.print(f"  {i}. [cyan]{key}[/]: {description}{recommended}")
                methods_list.append(key)

            # Ask user to select a method
            try:
                selection = click.prompt(
                    "\nSelect installation method", type=int, default=methods_list.index(method_id) + 1
                )
                if 1 <= selection <= len(methods_list):
                    method_id = methods_list[selection - 1]
                    selected_method = installations[method_id]
            except (ValueError, click.Abort):
                console.print("[yellow]Using default installation method.[/]")

        # Extract installation details
        if selected_method:
            # Use the method's type as the installation method if available, otherwise use the key
            installation_method = selected_method.get("type")
            if not installation_method or installation_method == "unknown":
                installation_method = method_id

            install_command = selected_method.get("command", install_command)
            install_args = selected_method.get("args", install_args)
            package_name = selected_method.get("package", package_name)
            env_vars = selected_method.get("env", env_vars)

        console.print(f"\n[green]Using [bold]{installation_method}[/] installation method[/]")

    # Configure the server
    with Progress(SpinnerColumn(), TextColumn("[bold green]{task.description}[/]"), console=console) as progress:
        # Save metadata to server directory
        progress.add_task("Saving server metadata...", total=None)
        metadata_path = os.path.join(server_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(server_metadata, f, indent=2)

        # Configure the server
        progress.add_task(f"Configuring {server_name}...", total=None)

        # Get all available arguments from the server metadata
        all_arguments = server_metadata.get("arguments", {})

        required_args = {}
        # Process variables to store in config
        processed_variables = {}
        processed_env = {}

        # First, prompt for all defined arguments even if they're not in env_vars
        progress.stop()
        if all_arguments:
            console.print("\n[bold]Configure server arguments:[/]")

            for arg_name, arg_info in all_arguments.items():
                description = arg_info.get("description", "")
                is_required = arg_info.get("required", False)
                example = arg_info.get("example", "")
                example_text = f" (example: {example})" if example else ""

                # Build prompt text
                prompt_text = f"Enter value for {arg_name}{example_text}"
                if description:
                    prompt_text += f"\n{description}"

                # Add required indicator
                if is_required:
                    required_args[arg_name] = arg_info
                    prompt_text += " (required)"
                else:
                    prompt_text += " (optional, press Enter to skip)"

                # Check if the argument is already set in environment
                env_value = os.environ.get(arg_name, "")

                if env_value:
                    # Show the existing value as default
                    console.print(f"[green]Found {arg_name} in environment: {env_value}[/]")
                    try:
                        user_value = click.prompt(
                            prompt_text,
                            default=env_value,
                            hide_input="token" in arg_name.lower()
                            or "key" in arg_name.lower()
                            or "secret" in arg_name.lower(),
                        )
                        if user_value != env_value:
                            # User provided a different value
                            processed_variables[arg_name] = user_value
                        else:
                            # User use environment value
                            processed_variables[arg_name] = env_value
                    except click.Abort:
                        pass
                else:
                    # No environment value
                    try:
                        if is_required:
                            # Required argument must have a value
                            user_value = click.prompt(
                                prompt_text,
                                hide_input="token" in arg_name.lower()
                                or "key" in arg_name.lower()
                                or "secret" in arg_name.lower(),
                            )
                            processed_variables[arg_name] = user_value
                        else:
                            # Optional argument can be skipped
                            user_value = click.prompt(
                                prompt_text,
                                default="",
                                show_default=False,
                                hide_input="token" in arg_name.lower()
                                or "key" in arg_name.lower()
                                or "secret" in arg_name.lower(),
                            )
                            # Only add non-empty values to the environment
                            if user_value and user_value.strip():
                                processed_variables[arg_name] = user_value
                            # Explicitly don't add anything if the user leaves it blank
                    except click.Abort:
                        if is_required:
                            console.print(f"[yellow]Warning: Required argument {arg_name} not provided.[/]")

            # Resume progress display
            progress = Progress(SpinnerColumn(), TextColumn("[bold green]{task.description}[/]"), console=console)
            progress.start()
            progress.add_task(f"Configuring {server_name}...", total=None)

        # Now process the replacement of environment variables
        for key, value in env_vars.items():
            processed_env[key] = value

            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # For required arguments, prompt the user if not in environment
                env_value = os.environ.get(key, "")

                if not env_value and key in required_args and key not in processed_variables:
                    progress.stop()
                    console.print(f"[yellow]Warning:[/] Required argument {key} is not set in environment")

                    # Prompt for the value
                    arg_info = required_args.get(key, {})
                    description = arg_info.get("description", "")
                    try:
                        user_value = click.prompt(
                            f"Enter value for {key} ({description})",
                            hide_input="token" in key.lower() or "key" in key.lower(),
                        )
                        processed_env[key] = user_value
                    except click.Abort:
                        console.print("[yellow]Will store the reference to environment variable instead.[/]")
                        processed_env[key] = value  # Store the reference as-is

                    # Resume progress
                    progress = Progress(
                        SpinnerColumn(), TextColumn("[bold green]{task.description}[/]"), console=console
                    )
                    progress.start()
                    progress.add_task(f"Configuring {server_name}...", total=None)
                else:
                    # Store reference to environment variable
                    processed_env[key] = processed_variables.get(key, env_value)
            else:
                processed_env[key] = value

    # replace arguments with values
    processed_args = []
    for arg in install_args:
        matched = re.match(r"\$\{(.*?)\}", arg)
        if matched:
            original, key = matched.group(0), matched.group(1)
            if key not in processed_variables:
                # not required, remove the argument from args
                continue
            replaced_arg = arg.replace(original, processed_variables.get(key, arg))
            processed_args.append(replaced_arg)
        else:
            processed_args.append(arg)

    # Get actual MCP execution command, args, and env from the selected installation method
    # This ensures we use the actual server command information instead of placeholders
    if selected_method:
        mcp_command = selected_method.get("command", install_command)
        mcp_args = processed_args
        # Env vars are already processed above
    else:
        mcp_command = install_command
        mcp_args = processed_args

    # Create server configuration using FullServerConfig
    full_server_config = FullServerConfig(
        name=config_name,
        display_name=display_name,
        description=description,
        command=mcp_command,  # Use the actual MCP server command
        args=mcp_args,  # Use the actual MCP server arguments
        env=processed_env,
        # Use the simplified installation method
        installation=installation_method,
    )

    if scope_type == ScopeType.CLIENT:
        # Add the server to the client configuration
        success = client_add_server(target_name, full_server_config.to_server_config(), force)
    else:
        # Add the server to the profile configuration
        success = profile_add_server(target_name, full_server_config.to_server_config(), force)

    if success:
        # Server has been successfully added to the client configuration
        console.print(f"[bold green]Successfully added {display_name} to {target_name}![/]")

        # Display usage examples if available
        examples = server_metadata.get("examples", [])
        if examples:
            console.print("\n[bold]Usage Examples:[/]")
            for i, example in enumerate(examples, 1):
                title = example.get("title", f"Example {i}")
                description = example.get("description", "")
                prompt = example.get("prompt", "")

                console.print(f"  [cyan]{title}[/]: {description}")
                if prompt:
                    console.print(f'  Try: [italic]"{prompt}"[/]\n')
    else:
        console.print(f"[bold red]Failed to add {server_name} to {target_name}.[/]")
