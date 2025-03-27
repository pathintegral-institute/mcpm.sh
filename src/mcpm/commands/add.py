"""
Add command for adding MCP servers directly to client configurations
"""

import os
import json
from datetime import datetime

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from mcpm.utils.repository import RepositoryManager
from mcpm.utils.server_config import ServerConfig
from mcpm.utils.client_manager import get_active_client, get_active_client_manager, get_active_client_info

console = Console()
repo_manager = RepositoryManager()

@click.command()
@click.argument("server_name")
@click.option("--force", is_flag=True, help="Force reinstall if server is already installed")
def add(server_name, force=False):
    """Add an MCP server to a client configuration.
    
    Examples:
        mcpm add time
        mcpm add everything --force
    """
    # Get the active client info
    client = get_active_client()
    if not client:
        console.print("[bold red]Error:[/] No active client found.")
        console.print("Please set an active client with 'mcpm client set <client>'.")
        return
    console.print(f"[yellow]Using active client: {client}[/]")
    
    # Get client manager
    client_manager = get_active_client_manager()
    if client_manager is None:
        console.print(f"[bold red]Error:[/] Unsupported client '{client}'.")
        return
    
    # Check if server already exists in client config
    existing_server = client_manager.get_server(server_name)
    if existing_server and not force:
        console.print(f"[yellow]Server '{server_name}' is already added to {client}.[/]")
        console.print("Use '--force' to overwrite the existing configuration.")
        return
    
    # Get server metadata from repository
    server_metadata = repo_manager.get_server_metadata(server_name)
    if not server_metadata:
        console.print(f"[bold red]Error:[/] Server '{server_name}' not found in registry.")
        console.print(f"Available servers: {', '.join(repo_manager._fetch_servers().keys())}")
        return
    
    # Display server information
    display_name = server_metadata.get("display_name", server_name)
    description = server_metadata.get("description", "No description available")
    available_version = server_metadata.get("version")
    author_info = server_metadata.get("author", {})
    
    console.print(f"\n[bold]{display_name}[/] ({server_name}) v{available_version}")
    console.print(f"[dim]{description}[/]")
    
    if author_info:
        author_name = author_info.get("name", "Unknown")
        author_url = author_info.get("url", "")
        console.print(f"[dim]Author: {author_name} {author_url}[/]")
    
    # Get client display name from the utility
    _, client_display_name, _ = get_active_client_info()
    
    # Confirm addition
    if not force and not Confirm.ask(f"Add this server to {client_display_name}?"):
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
    version = available_version
    
    # If no installation information is available, create minimal default values
    # This allows us to add the server config without full installation details
    method_key = "default"
    install_type = "manual"
    install_command = "echo"
    install_args = [f"Server {server_name} added to configuration"]
    package_name = None
    env_vars = {}
    required_args = {}
    
    # Process installation information if available
    selected_method = None  # Initialize selected_method to None to avoid UnboundLocalError
    if installations:
        # Find recommended installation method or default to the first one
        method_key = "default"
        
        # First check for a recommended method
        for key, method in installations.items():
            if method.get("recommended", False):
                selected_method = method
                method_key = key
                break
        
        # If no recommended method found, use the first one
        if not selected_method and installations:
            method_key = next(iter(installations))
            selected_method = installations[method_key]
        
        # If multiple methods are available and not forced, offer selection
        if len(installations) > 1 and not force:
            console.print("\n[bold]Available installation methods:[/]")
            methods_list = []
            
            for i, (key, method) in enumerate(installations.items(), 1):
                install_type = method.get("type", "unknown")
                description = method.get("description", f"{install_type} installation")
                recommended = " [green](recommended)[/]" if method.get("recommended", False) else ""
                
                console.print(f"  {i}. [cyan]{key}[/]: {description}{recommended}")
                methods_list.append(key)
            
            # Ask user to select a method
            try:
                selection = click.prompt("\nSelect installation method", type=int, default=methods_list.index(method_key) + 1)
                if 1 <= selection <= len(methods_list):
                    method_key = methods_list[selection - 1]
                    selected_method = installations[method_key]
            except (ValueError, click.Abort):
                console.print("[yellow]Using default installation method.[/]")
        
        # Extract installation details
        if selected_method:
            install_type = selected_method.get("type", install_type)
            install_command = selected_method.get("command", install_command)
            install_args = selected_method.get("args", install_args)
            package_name = selected_method.get("package", package_name)
            env_vars = selected_method.get("env", env_vars)
            required_args = server_metadata.get("required_args", required_args)
        
        console.print(f"\n[green]Using {install_type} installation method: [bold]{method_key}[/][/]")
    
    # Configure the server
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]{task.description}[/]"),
        console=console
    ) as progress:
        # Save metadata to server directory
        progress.add_task("Saving server metadata...", total=None)
        metadata_path = os.path.join(server_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(server_metadata, f, indent=2)
        
        # Configure the server
        progress.add_task(f"Configuring {server_name} v{version}...", total=None)
        
        # Get all available arguments from the server metadata
        all_arguments = server_metadata.get("arguments", {})
        
        # Process environment variables to store in config
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
                            hide_input="token" in arg_name.lower() or "key" in arg_name.lower() or "secret" in arg_name.lower()
                        )
                        if user_value != env_value:
                            # User provided a different value
                            processed_env[arg_name] = user_value
                        else:
                            # User kept the environment value
                            processed_env[arg_name] = f"${{{arg_name}}}"
                    except click.Abort:
                        # Keep environment reference on abort
                        processed_env[arg_name] = f"${{{arg_name}}}"
                else:
                    # No environment value
                    try:
                        if is_required:
                            # Required argument must have a value
                            user_value = click.prompt(
                                prompt_text,
                                hide_input="token" in arg_name.lower() or "key" in arg_name.lower() or "secret" in arg_name.lower()
                            )
                            processed_env[arg_name] = user_value
                        else:
                            # Optional argument can be skipped
                            user_value = click.prompt(
                                prompt_text,
                                default="",
                                show_default=False,
                                hide_input="token" in arg_name.lower() or "key" in arg_name.lower() or "secret" in arg_name.lower()
                            )
                            # Only add non-empty values to the environment
                            if user_value and user_value.strip():
                                processed_env[arg_name] = user_value
                            # Explicitly don't add anything if the user leaves it blank
                    except click.Abort:
                        if is_required:
                            console.print(f"[yellow]Warning: Required argument {arg_name} not provided.[/]")
                            # Store as environment reference even if missing
                            processed_env[arg_name] = f"${{{arg_name}}}"
            
            # Resume progress display
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold green]{task.description}[/]"),
                console=console
            )
            progress.start()
            progress.add_task(f"Configuring {server_name} v{version}...", total=None)
        
        # Now process any remaining environment variables from the installation method
        for key, value in env_vars.items():
            # Skip if we already processed this key
            if key in processed_env:
                continue
                
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var_name = value[2:-1]  # Extract variable name from ${NAME}
                is_required = env_var_name in required_args
                
                # For required arguments, prompt the user if not in environment
                env_value = os.environ.get(env_var_name, "")
                
                if not env_value and is_required:
                    progress.stop()
                    console.print(f"[yellow]Warning:[/] Required argument {env_var_name} is not set in environment")
                    
                    # Prompt for the value
                    arg_info = required_args.get(env_var_name, {})
                    description = arg_info.get("description", "")
                    try:
                        user_value = click.prompt(
                            f"Enter value for {env_var_name} ({description})", 
                            hide_input="token" in env_var_name.lower() or "key" in env_var_name.lower()
                        )
                        processed_env[key] = user_value
                    except click.Abort:
                        console.print("[yellow]Will store the reference to environment variable instead.[/]")
                        processed_env[key] = value  # Store the reference as-is
                    
                    # Resume progress
                    progress = Progress(
                        SpinnerColumn(),
                        TextColumn("[bold green]{task.description}[/]"),
                        console=console
                    )
                    progress.start()
                    progress.add_task(f"Configuring {server_name} v{version}...", total=None)
                else:
                    # Store reference to environment variable
                    processed_env[key] = value
            else:
                processed_env[key] = value
        
    # Get actual MCP execution command, args, and env from the selected installation method
    # This ensures we use the actual server command information instead of placeholders
    if selected_method:
        mcp_command = selected_method.get("command", install_command)
        mcp_args = selected_method.get("args", install_args)
        # Env vars are already processed above
    else:
        mcp_command = install_command
        mcp_args = install_args

    # Create server configuration using ServerConfig
    server_config = ServerConfig(
        name=server_name,
        path=server_dir,
        display_name=display_name,
        description=description,
        version=version,
        status="stopped",
        command=mcp_command,  # Use the actual MCP server command
        args=mcp_args,        # Use the actual MCP server arguments
        env_vars=processed_env,
        install_date=datetime.now().strftime("%Y-%m-%d"),
        package=package_name,
        installation_method=method_key,
        installation_type=install_type
    )
    
    # Add the server to the client configuration
    success = client_manager.add_server(server_config)
    
    if success:
        # Server has been successfully added to the client configuration
        console.print(f"[bold green]Successfully added {display_name} v{version} to {client_display_name}![/]")
        
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
                    console.print(f"  Try: [italic]\"{prompt}\"[/]\n")
    else:
        console.print(f"[bold red]Failed to add {server_name} to {client}.[/]")
