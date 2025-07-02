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
from mcpm.global_config import GlobalConfigManager
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.config import ConfigManager

profile_config_manager = ProfileConfigManager()
global_config_manager = GlobalConfigManager()
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
    console.print(f"You can now edit this profile to add servers using 'mcpm profile edit {profile}'\n")


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

    \b
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
        console.print(f"  mcpm profile edit {profile_name}")
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
        ctx.invoke(share, command=command_str, port=port, address=address, http=http, timeout=timeout, retry=retry)

    else:
        # Multiple servers - would need router or multiplexed approach
        console.print("[yellow]Multi-server profile sharing not yet implemented.[/]")
        console.print("[dim]For now, you can share individual servers with 'mcpm share <server-name>'[/]")
        console.print()
        console.print("[cyan]Servers in this profile:[/]")
        for server_config in profile_servers:
            console.print(f"  • {server_config.name}")

        return 1


def interactive_profile_edit(profile_name: str, all_servers: dict, current_servers: set):
    """Interactive profile edit using InquirerPy"""
    import sys

    # Check if we're in a terminal that supports interactive input
    if not sys.stdin.isatty():
        console.print("[yellow]Interactive editing not available in this environment[/]")
        console.print("[dim]Use --name and --servers options for non-interactive editing[/]")
        return None

    try:
        from InquirerPy import prompt
        from InquirerPy.base.control import Choice

        # Use list comprehension to build server list avoiding Click conflicts
        server_names = [name for name in all_servers]

        # Prepare server choices for InquirerPy
        server_choices = []
        for server_name in server_names:
            server_config = all_servers[server_name]
            command = getattr(server_config, "command", "custom")
            if hasattr(command, "__iter__") and not isinstance(command, str):
                command = " ".join(str(x) for x in command)
            
            server_choices.append(Choice(
                value=server_name,
                name=f"{server_name} ({command})",
                enabled=True
            ))

        # Create the interactive form
        questions = [
            {
                "type": "input",
                "name": "name",
                "message": "Profile name:",
                "default": profile_name,
                "validate": lambda text: len(text.strip()) > 0 or "Profile name cannot be empty"
            },
            {
                "type": "checkbox",
                "name": "servers",
                "message": "Select servers to include in this profile:",
                "choices": server_choices,
                "default": [name for name in current_servers],
                "instruction": "(Use arrow keys to navigate, space to select/deselect, enter to confirm)"
            }
        ]

        # Clear any remaining command line arguments to avoid conflicts
        import sys
        import os
        original_argv = sys.argv[:]
        
        # Clear all command line arguments that might interfere
        sys.argv = [sys.argv[0]]  # Keep only script name
        
        try:
            answers = prompt(questions, style_override=False)
        finally:
            # Restore original argv
            sys.argv = original_argv

        if not answers:
            return {"cancelled": True}

        return {
            "cancelled": False,
            "name": answers["name"].strip(),
            "servers": set(answers["servers"])
        }

    except ImportError:
        console.print("[yellow]InquirerPy not available, falling back to simple prompts[/]")
        return None
    except (KeyboardInterrupt, EOFError):
        return {"cancelled": True}
    except Exception as e:
        console.print(f"[red]Error running interactive form: {e}[/]")
        return None


@profile.command(name="edit")
@click.argument("profile_name")
@click.option("--name", type=str, help="New profile name (non-interactive)")
@click.option("--servers", type=str, help="Comma-separated list of server names to include (non-interactive)")
@click.help_option("-h", "--help")
def edit_profile(profile_name, name, servers):
    """Edit a profile's name and server selection.

    By default, opens an advanced interactive form editor that allows you to:
    - Change the profile name with real-time validation
    - Select servers using a modern checkbox interface with search
    - Navigate with arrow keys, select with space, and search by typing

    For non-interactive usage, use --name and/or --servers options.

    Examples:

    \b
        mcpm profile edit web-dev                           # Interactive form
        mcpm profile edit web-dev --name frontend-tools    # Rename only
        mcpm profile edit web-dev --servers time,sqlite    # Set servers only
        mcpm profile edit web-dev --name new-name --servers time,weather  # Both
    """
    # Check if profile exists
    existing_servers = profile_config_manager.get_profile(profile_name)
    if existing_servers is None:
        console.print(f"[red]Error: Profile '[bold]{profile_name}[/]' not found[/]")
        console.print()
        console.print("[yellow]Available options:[/]")
        console.print("  • Run 'mcpm profile ls' to see available profiles")
        console.print("  • Run 'mcpm profile create {name}' to create a profile")
        return 1

    # Detect if this is non-interactive mode
    is_non_interactive = name is not None or servers is not None

    if is_non_interactive:
        # Non-interactive mode
        console.print(f"[bold green]Editing Profile: [cyan]{profile_name}[/] [dim](non-interactive)[/]")
        console.print()

        # Handle profile name
        new_name = name if name is not None else profile_name

        # Check if new name conflicts with existing profiles (if changed)
        if new_name != profile_name and profile_config_manager.get_profile(new_name) is not None:
            console.print(f"[red]Error: Profile '[bold]{new_name}[/]' already exists[/]")
            return 1

        # Handle server selection
        if servers is not None:
            # Parse comma-separated server list
            requested_servers = [s.strip() for s in servers.split(",") if s.strip()]

            # Get all available servers for validation
            all_servers = global_config_manager.list_servers()
            if not all_servers:
                console.print("[yellow]No servers found in global configuration[/]")
                console.print("[dim]Install servers first with 'mcpm install <server-name>'[/]")
                return 1

            # Validate requested servers exist
            invalid_servers = [s for s in requested_servers if s not in all_servers]
            if invalid_servers:
                console.print(f"[red]Error: Server(s) not found: {', '.join(invalid_servers)}[/]")
                console.print()
                console.print("[yellow]Available servers:[/]")
                for server_name in sorted(all_servers.keys()):
                    console.print(f"  • {server_name}")
                return 1

            selected_servers = set(requested_servers)
        else:
            # Keep current server selection
            selected_servers = {server.name for server in existing_servers} if existing_servers else set()
            # Get all servers for applying changes
            all_servers = global_config_manager.list_servers()

    else:
        # Interactive mode using InquirerPy
        console.print(f"[bold green]Opening Interactive Profile Editor: [cyan]{profile_name}[/]")
        console.print("[dim]Use arrow keys to navigate, space to select/deselect, type to search, enter to confirm[/]")
        console.print()

        # Get all available servers from global configuration
        all_servers = global_config_manager.list_servers()

        if not all_servers:
            console.print("[yellow]No servers found in global configuration[/]")
            console.print("[dim]Install servers first with 'mcpm install <server-name>'[/]")
            return 1

        # Get currently selected servers
        current_server_names = {server.name for server in existing_servers} if existing_servers else set()

        # Run the interactive form
        try:
            result = interactive_profile_edit(profile_name, all_servers, current_server_names)

            if result is None:
                console.print("[yellow]Interactive editing not available, falling back to non-interactive mode[/]")
                console.print("[dim]Use --name and --servers options to edit the profile[/]")
                return 1

            if result.get("cancelled", True):
                console.print("[yellow]Profile editing cancelled[/]")
                return 0

            # Extract results from InquirerPy form
            new_name = result["name"]
            selected_servers = result["servers"]

            # Check if new name conflicts with existing profiles (if changed)
            if new_name != profile_name and profile_config_manager.get_profile(new_name) is not None:
                console.print(f"[red]Error: Profile '[bold]{new_name}[/]' already exists[/]")
                return 1

        except Exception as e:
            console.print(f"[red]Error running interactive editor: {e}[/]")
            return 1

    console.print()

    # Show summary
    console.print("[bold]Summary of changes:[/]")
    console.print(f"Profile name: [cyan]{profile_name}[/] → [cyan]{new_name}[/]")
    console.print(f"Selected servers: [cyan]{len(selected_servers)} servers[/]")

    if selected_servers:
        for server_name in sorted(selected_servers):
            console.print(f"  • {server_name}")
    else:
        console.print("  [dim]No servers selected[/]")

    console.print()

    # Confirmation (only for non-interactive mode, InquirerPy handles its own confirmation)
    if is_non_interactive:
        console.print("[bold green]Applying changes...[/]")

    # Apply changes
    try:
        # If name changed, create new profile and delete old one
        if new_name != profile_name:
            # Create new profile with selected servers
            profile_config_manager.new_profile(new_name)

            # Add selected servers to new profile
            for server_name in selected_servers:
                server_config = all_servers[server_name]
                profile_config_manager.set_profile(new_name, server_config)

            # Delete old profile
            profile_config_manager.delete_profile(profile_name)

            console.print(f"[green]✅ Profile renamed from '[cyan]{profile_name}[/]' to '[cyan]{new_name}[/]'[/]")
        else:
            # Same name, just update servers
            # Clear current servers
            profile_config_manager.clear_profile(profile_name)

            # Add selected servers
            for server_name in selected_servers:
                server_config = all_servers[server_name]
                profile_config_manager.set_profile(profile_name, server_config)

            console.print(f"[green]✅ Profile '[cyan]{profile_name}[/]' updated[/]")

        console.print(f"[green]✅ {len(selected_servers)} servers configured in profile[/]")

    except Exception as e:
        console.print(f"[red]Error updating profile: {e}[/]")
        return 1

    return 0


@profile.command(name="rm")
@click.argument("profile_name")
@click.option("--force", "-f", is_flag=True, help="Force removal without confirmation")
@click.help_option("-h", "--help")
def remove_profile(profile_name, force):
    """Remove a profile.

    Deletes the specified profile and all its server associations.
    The servers themselves remain in the global configuration.

    Examples:

    \b
        mcpm profile rm old-profile         # Remove with confirmation
        mcpm profile rm old-profile --force # Remove without confirmation
    """
    # Check if profile exists
    if profile_config_manager.get_profile(profile_name) is None:
        console.print(f"[red]Error: Profile '[bold]{profile_name}[/]' not found[/]")
        console.print()
        console.print("[yellow]Available options:[/]")
        console.print("  • Run 'mcpm profile ls' to see available profiles")
        return 1

    # Get profile info for confirmation
    profile_servers = profile_config_manager.get_profile(profile_name)
    server_count = len(profile_servers) if profile_servers else 0

    # Confirmation (unless forced)
    if not force:
        from rich.prompt import Confirm

        console.print(f"[yellow]About to remove profile '[bold]{profile_name}[/]'[/]")
        if server_count > 0:
            console.print(f"[dim]This profile contains {server_count} server(s)[/]")
            console.print("[dim]The servers will remain in global configuration[/]")
        console.print()

        confirm_removal = Confirm.ask("Are you sure you want to remove this profile?", default=False)

        if not confirm_removal:
            console.print("[yellow]Profile removal cancelled[/]")
            return 0

    # Remove the profile
    success = profile_config_manager.delete_profile(profile_name)

    if success:
        console.print(f"[green]✅ Profile '[cyan]{profile_name}[/]' removed successfully[/]")
        if server_count > 0:
            console.print(f"[dim]{server_count} server(s) remain available in global configuration[/]")
    else:
        console.print(f"[red]Error removing profile '[bold]{profile_name}[/]'[/]")
        return 1

    return 0


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

    \b
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
            console.print("  • Run 'mcpm profile create {name}' to create a profile")
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
        console.print(f"  mcpm profile edit {profile_name}")
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
                    command, env=env, cwd=cwd, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr
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
