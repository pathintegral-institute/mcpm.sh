import json
import os
import subprocess
import sys
import time
from threading import Thread

import click
from rich.console import Console
from rich.table import Table

from mcpm.clients.client_registry import ClientRegistry
from mcpm.core.schema import CustomServerConfig, STDIOServerConfig
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.config import ConfigManager

profile_config_manager = ProfileConfigManager()
console = Console()


@click.group()
@click.help_option("-h", "--help")
def profile():
    """Manage MCPM profiles."""
    pass


@profile.command(name="ls")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed server information")
@click.help_option("-h", "--help")
def list(verbose=False):
    """List all MCPM profiles."""
    profiles = profile_config_manager.list_profiles()
    if not profiles:
        console.print("\n[yellow]No profiles found.[/]\n")
        return
    console.print(f"\n[green]Found {len(profiles)} profile(s)[/]\n")
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
            row.append("\n".join(details))
        table.add_row(*row)
    console.print(table)


@profile.command(name="create")
@click.argument("profile")
@click.option("--force", is_flag=True, help="Force add even if profile already exists")
@click.help_option("-h", "--help")
def create(profile, force=False):
    """Create a new MCPM profile."""
    if profile_config_manager.get_profile(profile) is not None and not force:
        console.print(f"[bold red]Error:[/] Profile '{profile}' already exists.")
        console.print("Use '--force' to overwrite the existing profile.")
        return

    profile_config_manager.new_profile(profile)

    console.print(f"\n[green]Profile '{profile}' created successfully.[/]\n")
    console.print(f"You can now tag servers with this profile using 'mcpm profile add {profile} <server_name>'\n")


@profile.command(name="add")
@click.argument("profile_name")
@click.argument("server_name")
@click.help_option("-h", "--help")
def add_server(profile_name, server_name):
    """Tag a server with a profile.
    
    Adds a server to a profile's tag list. Servers remain in the global
    configuration but are organized by profile tags.
    
    Examples:
        mcpm profile add web-dev mcp-server-browse    # Tag browse server with web-dev
        mcpm profile add ai gpt-4                    # Tag gpt-4 server with ai profile
    """
    # Check if profile exists
    if profile_config_manager.get_profile(profile_name) is None:
        console.print(f"[red]Error: Profile '[bold]{profile_name}[/]' not found[/]")
        console.print(f"[dim]Create it first with: mcpm profile create {profile_name}[/]")
        return 1
    
    # Find the server in the global configuration
    from mcpm.commands.run import find_installed_server
    server_config, location = find_installed_server(server_name)
    
    if not server_config:
        console.print(f"[red]Error: Server '[bold]{server_name}[/]' not found[/]")
        console.print()
        console.print("[yellow]Available options:[/]")
        console.print("  • Run 'mcpm ls' to see installed servers")
        console.print("  • Run 'mcpm search {name}' to find available servers")
        console.print("  • Run 'mcpm install {name}' to install a server")
        return 1
    
    # Convert to ServerConfig for profile storage
    from mcpm.core.schema import STDIOServerConfig
    try:
        # Create a server config object for the profile
        server_config_obj = STDIOServerConfig(
            name=server_name,
            command=server_config["command"][0] if server_config.get("command") else "unknown",
            args=server_config["command"][1:] if server_config.get("command") and len(server_config["command"]) > 1 else [],
            env=server_config.get("env", {}),
            cwd=server_config.get("cwd")
        )
        
        # Add to profile
        profile_config_manager.set_profile(profile_name, server_config_obj)
        
        console.print(f"[green]✅ Tagged server '[cyan]{server_name}[/]' with profile '[cyan]{profile_name}[/]'[/]")
        console.print(f"[dim]Found server in: {location}[/]")
        
    except Exception as e:
        console.print(f"[red]Error adding server to profile: {e}[/]")
        return 1


@profile.command(name="remove") 
@click.argument("profile_name")
@click.argument("server_name")
@click.help_option("-h", "--help")
def remove_server(profile_name, server_name):
    """Remove profile tag from a server.
    
    Removes a server from a profile's tag list. The server remains in the
    global configuration and other profile tags.
    
    Examples:
        mcpm profile remove web-dev mcp-server-browse    # Remove web-dev tag from browse server
        mcpm profile remove ai gpt-4                    # Remove ai tag from gpt-4 server
    """
    # Check if profile exists
    if profile_config_manager.get_profile(profile_name) is None:
        console.print(f"[red]Error: Profile '[bold]{profile_name}[/]' not found[/]")
        return 1
    
    # Remove server from profile
    if profile_config_manager.remove_server(profile_name, server_name):
        console.print(f"[green]✅ Removed '[cyan]{server_name}[/]' from profile '[cyan]{profile_name}[/]'[/]")
    else:
        console.print(f"[yellow]Server '[bold]{server_name}[/]' was not tagged with profile '[bold]{profile_name}[/]'[/]")
        return 1


@profile.command(name="share")
@click.argument("profile_name")
@click.option("--port", type=int, default=None, help="Port for the SSE server (random if not specified)")
@click.option("--address", type=str, default=None, help="Remote address for tunnel, use share.mcpm.sh if not specified")
@click.option(
    "--http", is_flag=True, default=False, help="Use HTTP instead of HTTPS. NOT recommended to use on public networks."
)
@click.option(
    "--timeout",
    type=int,
    default=30,
    help="Timeout in seconds to wait for server requests before considering the server inactive",
)
@click.option("--retry", type=int, default=0, help="Number of times to automatically retry on error (default: 0)")
@click.help_option("-h", "--help")
def share_profile(profile_name, port, address, http, timeout, retry):
    """Create a secure public tunnel to all servers in a profile.
    
    This command runs all servers in a profile and creates a shared tunnel
    to make them accessible remotely. Each server gets its own endpoint.
    
    Examples:
        mcpm profile share web-dev           # Share all servers in web-dev profile
        mcpm profile share ai --port 5000    # Share ai profile on specific port
        mcpm profile share data --retry 3    # Share with retry on errors
    """
    # Check if profile exists
    profile_servers = profile_config_manager.get_profile(profile_name)
    if profile_servers is None:
        console.print(f"[red]Error: Profile '[bold]{profile_name}[/]' not found[/]")
        console.print()
        console.print("[yellow]Available options:[/]")
        console.print("  • Run 'mcpm profile ls' to see available profiles")
        console.print("  • Run 'mcpm profile create {name}' to create a profile")
        return 1
    
    # Get servers in profile
    if not profile_servers:
        console.print(f"[yellow]Profile '[bold]{profile_name}[/]' has no servers configured[/]")
        console.print()
        console.print("[dim]Add servers to this profile with:[/]")
        console.print(f"  mcpm profile add {profile_name} <server-name>")
        return 0
    
    console.print(f"[bold green]Sharing profile '[cyan]{profile_name}[/]' with {len(profile_servers)} server(s)[/]")
    
    # For now, we'll use the router approach or share the first server
    # In a full implementation, this would set up a multiplexed sharing system
    if len(profile_servers) == 1:
        # Single server - use direct sharing
        server_config = profile_servers[0]
        server_dict = server_config.model_dump()
        
        if "command" not in server_dict:
            console.print(f"[red]Error: Server '{server_config.name}' has no command specified[/]")
            return 1
        
        command = server_dict["command"]
        if isinstance(command, list):
            command_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in command)
        else:
            command_str = str(command)
        
        console.print(f"[cyan]Sharing server: {server_config.name}[/]")
        console.print(f"[dim]Command: {command_str}[/]")
        
        # Import and call the share command
        from mcpm.commands.share import share
        
        # Create a context and invoke the share command
        import click
        ctx = click.Context(share)
        ctx.invoke(share, 
                  command=command_str,
                  port=port,
                  address=address, 
                  http=http,
                  timeout=timeout,
                  retry=retry)
        
    else:
        # Multiple servers - would need router or multiplexed approach
        console.print("[yellow]Multi-server profile sharing not yet implemented.[/]")
        console.print("[dim]For now, you can share individual servers with 'mcpm share <server-name>'[/]")
        console.print()
        console.print("[cyan]Servers in this profile:[/]")
        for server_config in profile_servers:
            console.print(f"  • {server_config.name}")
        
        return 1


@profile.command("rm")
@click.argument("profile_name")
@click.help_option("-h", "--help")
def remove(profile_name):
    """Delete an MCPM profile."""
    if not profile_config_manager.delete_profile(profile_name):
        console.print(f"[bold red]Error:[/] Profile '{profile_name}' not found.")
        return
    # Check whether any client is associated with the deleted profile
    clients = ClientRegistry.get_supported_clients()
    for client in clients:
        client_manager = ClientRegistry.get_client_manager(client)
        if client_manager:
            profile_server = client_manager.get_server(profile_name)
            if profile_server:
                # Deactivate the profile in this client
                client_manager.deactivate_profile(profile_name)
                console.print(f"\n[green]Profile '{profile_name}' removed successfully from client '{client}'.[/]\n")

    # v2.0: No active profile concept - profiles are just tags

    console.print(f"\n[green]Profile '{profile_name}' deleted successfully.[/]\n")


@profile.command()
@click.argument("profile_name")
@click.help_option("-h", "--help")
def rename(profile_name):
    """Rename an MCPM profile."""
    new_profile_name = click.prompt("Enter new profile name", type=str)
    if profile_config_manager.get_profile(new_profile_name) is not None:
        console.print(f"[bold red]Error:[/] Profile '{new_profile_name}' already exists.")
        return
    if not profile_config_manager.rename_profile(profile_name, new_profile_name):
        console.print(f"[bold red]Error:[/] Profile '{profile_name}' not found.")
        return
    # Check whether any client is associated with the profile to be renamed
    clients = ClientRegistry.get_supported_clients()
    config_manager = ConfigManager()
    for client in clients:
        client_manager = ClientRegistry.get_client_manager(client)
        if client_manager:
            profile_server = client_manager.get_server(profile_name)
            if profile_server:
                # fresh the config
                client_manager.deactivate_profile(profile_name)
                client_manager.activate_profile(new_profile_name, config_manager.get_router_config())
                console.print(f"\n[green]Profile '{profile_name}' replaced successfully in client '{client}'.[/]\n")

    # v2.0: No active profile concept - profiles are just tags

    console.print(f"\n[green]Profile '{profile_name}' renamed to '{new_profile_name}' successfully.[/]\n")


@profile.command()
@click.argument("profile_name")
@click.option("--debug", is_flag=True, help="Show debug output")
@click.help_option("-h", "--help")
def run(profile_name, debug):
    """Execute all servers in a profile over stdio.
    
    Runs all servers tagged with the specified profile simultaneously,
    multiplexing their stdio streams. This is useful for running a complete
    development environment or a set of related servers.
    
    Examples:
        mcpm profile run web-dev     # Run all servers in web-dev profile
        mcpm profile run --debug ai  # Run ai profile with debug output
    """
    # Validate profile name
    if not profile_name or not profile_name.strip():
        console.print("[red]Error: Profile name cannot be empty[/]")
        return 1
    
    profile_name = profile_name.strip()
    
    # Check if profile exists
    try:
        profile_servers = profile_config_manager.get_profile(profile_name)
        if profile_servers is None:
            console.print(f"[red]Error: Profile '[bold]{profile_name}[/]' not found[/]")
            console.print()
            console.print("[yellow]Available options:[/]")
            console.print("  • Run 'mcpm profile ls' to see available profiles")
            console.print("  • Run 'mcpm profile add {name}' to create a profile")
            return 1
    except Exception as e:
        console.print(f"[red]Error accessing profile '{profile_name}': {e}[/]")
        return 1
    
    # Get servers in profile
    servers = []
    if profile_servers:
        # Convert ServerConfig objects to (name, dict) tuples for compatibility
        for server_config in profile_servers:
            server_dict = server_config.model_dump()
            servers.append((server_config.name, server_dict))
    
    if not servers:
        console.print(f"[yellow]Profile '[bold]{profile_name}[/]' has no servers configured[/]")
        console.print()
        console.print("[dim]Add servers to this profile with:[/]")
        console.print(f"  mcpm profile add {profile_name} <server-name>")
        return 0
    
    console.print(f"[bold green]Running profile '[cyan]{profile_name}[/]' with {len(servers)} server(s)[/]")
    
    if debug:
        console.print("[dim]Servers to run:[/]")
        for name, config in servers:
            console.print(f"  - {name}: {config.get('command', ['unknown'])}") 
    
    # Record profile usage
    try:
        from mcpm.commands.usage import record_profile_usage
        record_profile_usage(profile_name, "run")
    except ImportError:
        pass  # Usage tracking not available
    
    # Start all servers
    processes = []
    
    try:
        for server_name, server_config in servers:
            if "command" not in server_config:
                console.print(f"[yellow]Skipping '{server_name}': no command specified[/]", err=True)
                continue
            
            command = server_config["command"]
            if not isinstance(command, list) or not command:
                console.print(f"[yellow]Skipping '{server_name}': invalid command format[/]", err=True)
                continue
            
            # Set up environment
            env = os.environ.copy()
            if "env" in server_config:
                for key, value in server_config["env"].items():
                    env[key] = str(value)
            
            # Set working directory
            cwd = server_config.get("cwd")
            if cwd:
                cwd = os.path.expanduser(cwd)
            
            if debug:
                console.print(f"[dim]Starting {server_name}: {' '.join(command)}[/]", err=True)
            
            # Start process
            try:
                process = subprocess.Popen(
                    command,
                    env=env,
                    cwd=cwd,
                    stdin=sys.stdin,
                    stdout=sys.stdout,
                    stderr=sys.stderr
                )
                processes.append((server_name, process))
                
            except FileNotFoundError:
                console.print(f"[red]Error: Command not found for '{server_name}': {command[0]}[/]", err=True)
                continue
            except Exception as e:
                console.print(f"[red]Error starting '{server_name}': {e}[/]", err=True)
                continue
        
        if not processes:
            console.print("[red]Error: No servers could be started[/]")
            return 1
        
        console.print(f"[green]Started {len(processes)} server(s). Press Ctrl+C to stop all.[/]", err=True)
        
        # Wait for all processes
        return_codes = []
        try:
            # Wait for any process to complete
            while processes:
                time.sleep(0.1)
                completed = []
                
                for i, (name, process) in enumerate(processes):
                    if process.poll() is not None:
                        return_code = process.returncode
                        return_codes.append(return_code)
                        completed.append(i)
                        
                        if debug:
                            console.print(f"[dim]Server '{name}' exited with code {return_code}[/]", err=True)
                
                # Remove completed processes
                for i in reversed(completed):
                    processes.pop(i)
                
                # If any process failed, stop all others
                if any(code != 0 for code in return_codes):
                    break
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping all servers...[/]", err=True)
            
            # Terminate all remaining processes
            for name, process in processes:
                try:
                    process.terminate()
                    if debug:
                        console.print(f"[dim]Terminated {name}[/]", err=True)
                except Exception:
                    pass
            
            # Wait for processes to exit
            for name, process in processes:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    if debug:
                        console.print(f"[dim]Killed {name}[/]", err=True)
            
            return 130
        
        # Check final return codes
        if return_codes and all(code == 0 for code in return_codes):
            console.print("[green]All servers completed successfully[/]", err=True)
            return 0
        else:
            console.print("[red]One or more servers failed[/]", err=True)
            return 1
            
    except Exception as e:
        console.print(f"[red]Error running profile: {e}[/]", err=True)
        
        # Clean up any running processes
        for name, process in processes:
            try:
                process.terminate()
            except Exception:
                pass
        
        return 1
