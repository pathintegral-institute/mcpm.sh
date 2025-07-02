"""Profile run command."""

import os
import subprocess
import sys
import time

import click
from rich.console import Console

from mcpm.profile.profile_config import ProfileConfigManager

console = Console()
profile_config_manager = ProfileConfigManager()


@click.command()
@click.argument("profile_name")
@click.option("--debug", is_flag=True, help="Show debug output")
@click.help_option("-h", "--help")
def run(profile_name, debug):
    """Execute all servers in a profile over stdio.

    Runs all servers tagged with the specified profile simultaneously,
    multiplexing their stdio streams. This is useful for running a complete
    development environment or a set of related servers.

    Examples:

    \\b
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
            console.print("\\n[yellow]Stopping all servers...[/]", err=True)

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
