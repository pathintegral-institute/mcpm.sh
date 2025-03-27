"""
Install command for MCPM
"""

import os
import json
from datetime import datetime

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from mcpm.utils.repository import RepositoryManager
from mcpm.utils.config import ConfigManager
from mcpm.utils.client_detector import detect_installed_clients

console = Console()
repo_manager = RepositoryManager()
config_manager = ConfigManager()

@click.command()
@click.argument("server_name")
@click.option("--force", is_flag=True, help="Force reinstall if server is already installed")
def install(server_name, force=False):
    """[DEPRECATED] Install an MCP server.
    
    This command is deprecated. Please use 'mcpm add' instead, which directly
    adds servers to client configurations without using a global config.
    
    Examples:
        mcpm add time
        mcpm add github
        mcpm add everything --force
    """
    # Show deprecation warning
    console.print("[bold yellow]WARNING: The 'install' command is deprecated![/]")
    console.print("[yellow]Please use 'mcpm add' instead, which adds servers directly to client configurations.[/]")
    console.print("[yellow]Run 'mcpm add --help' for more information.[/]")
    console.print("")
    
    # Check if already installed
    existing_server = config_manager.get_server_info(server_name)
    if existing_server and not force:
        console.print(f"[yellow]Server '{server_name}' is already installed (v{existing_server.get('version', 'unknown')}).[/]")
        console.print("Use 'mcpm install --force' to reinstall or 'mcpm update' to update it to a newer version.")
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
    author_name = author_info.get("name", "Unknown")
    license_info = server_metadata.get("license", "Unknown")
    
    # Use the available version
    version = available_version
    
    # Display server information
    console.print("\n[bold cyan]Server Information[/]")
    console.print(f"[bold]{display_name}[/] [dim]v{version}[/]")
    console.print(f"[italic]{description}[/]")
    console.print()
    console.print(f"Author: {author_name}")
    console.print(f"License: {license_info}")
    console.print()
    
    # Check for required arguments in the new schema
    arguments = server_metadata.get("arguments", {})
    required_args = {k: v for k, v in arguments.items() if v.get("required", False)}
    needs_api_key = len(required_args) > 0
    
    if needs_api_key:
        console.print("\n[yellow]Note:[/] This server requires the following arguments:")
        for arg_name, arg_info in required_args.items():
            description = arg_info.get("description", "")
            example = arg_info.get("example", "")
            example_text = f" (e.g. '{example}')" if example else ""
            console.print(f"  [bold]{arg_name}[/]: {description}{example_text}")
    
    # Installation preparation
    if not force and existing_server:
        if not Confirm.ask(f"Server '{server_name}' is already installed. Do you want to reinstall?"):
            return
    
    # Create server directory
    server_dir = os.path.expanduser(f"~/.config/mcp/servers/{server_name}")
    os.makedirs(server_dir, exist_ok=True)
    
    # Get installation instructions from the new 'installations' field
    installations = server_metadata.get("installations", {})
    
    # Fall back to legacy 'installation' field if needed
    if not installations:
        installation = server_metadata.get("installation", {})
        if installation and installation.get("command") and installation.get("args"):
            installations = {"default": installation}
    
    if not installations:
        console.print(f"[bold red]Error:[/] No installation methods found for server '{server_name}'.")        
        return
    
    # Find recommended installation method or default to the first one
    selected_method = None
    method_key = None
    
    # First check for a recommended method
    for key, method in installations.items():
        if method.get("recommended", False):
            selected_method = method
            method_key = key
            break
    
    # If no recommended method found, use the first one
    if not selected_method:
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
    install_type = selected_method.get("type")
    install_command = selected_method.get("command")
    install_args = selected_method.get("args", [])
    package_name = selected_method.get("package")
    env_vars = selected_method.get("env", {})
    
    if not install_command or not install_args:
        console.print(f"[bold red]Error:[/] Invalid installation information for method '{method_key}'.")        
        return
    
    console.print(f"\n[green]Using {install_type} installation method: [bold]{method_key}[/][/]")
    
    # Download and install server
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]{task.description}[/]"),
        console=console
    ) as progress:
        # Download metadata
        progress.add_task("Downloading server metadata...", total=None)
        # Save metadata to server directory
        metadata_path = os.path.join(server_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(server_metadata, f, indent=2)
        
        # Configure the server (do not execute installation command)
        progress.add_task(f"Configuring {server_name} v{version}...", total=None)
        
        # Process environment variables to store in config
        processed_env = {}
        
        for key, value in env_vars.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"): 
                env_var_name = value[2:-1]  # Extract variable name from ${NAME}
                is_required = env_var_name in required_args
                
                # For required arguments, prompt the user if not in environment
                env_value = os.environ.get(env_var_name, "")
                
                if not env_value and is_required:
                    console.print(f"[yellow]Warning:[/] Required argument {env_var_name} is not set in environment")
                    
                    # Prompt for the value
                    arg_info = required_args[env_var_name]
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
                else:
                    # Store reference to environment variable
                    processed_env[key] = value
            else:
                processed_env[key] = value
        
        # Display the installation command (for information only)
        if install_command:
            full_command = [install_command] + install_args
            console.print(f"[dim]Installation command: {' '.join(full_command)}[/]")
            console.print("[green]Server has been configured and added to client.[/]")
    
    # Create server configuration
    server_info = {
        "name": server_name,
        "display_name": display_name,
        "version": version,
        "description": description,
        "status": "stopped",
        "install_date": datetime.now().strftime("%Y-%m-%d"),
        "path": server_dir,
        "package": package_name
    }
    
    # Add installation method information if available
    if method_key:
        server_info["installation_method"] = method_key
    if install_type:
        server_info["installation_type"] = install_type
    
    # Register the server in our config
    config_manager.register_server(server_name, server_info)
    
    console.print(f"[bold green]Successfully installed {display_name} v{version}![/]")
    
    # Handle client enablement - automatically enable for active client
    active_client = config_manager.get_active_client()
    
    # Always enable for active client, regardless of installation status
    if active_client:
        success = config_manager.enable_server_for_client(server_name, active_client)
        if success:
            console.print(f"[green]Enabled {server_name} for active client: {active_client}[/]")
        else:
            console.print(f"[yellow]Failed to enable {server_name} for {active_client}[/]")
        
        # Show additional info about client installation if client isn't installed
        installed_clients = detect_installed_clients()
        if not installed_clients.get(active_client, False):
            console.print(f"[dim]Note: {active_client} is configured but not detected as installed.[/]")
    
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
