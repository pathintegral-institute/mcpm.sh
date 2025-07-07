"""Interactive profile editing functionality using InquirerPy."""

import sys

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console

console = Console()


def interactive_profile_edit(profile_name: str, all_servers: dict, current_servers: set):
    """Interactive profile edit using InquirerPy"""
    # Check if we're in a terminal that supports interactive input
    if not sys.stdin.isatty():
        console.print("[yellow]Interactive editing not available in this environment[/]")
        console.print("[dim]Use --name and --servers options for non-interactive editing[/]")
        return None

    try:
        # Build server choices in a single loop
        server_choices = []
        for server_name, server_config in all_servers.items():
            command = getattr(server_config, "command", "custom")
            if hasattr(command, "__iter__") and not isinstance(command, str):
                command = " ".join(str(x) for x in command)

            # Set enabled=True only for servers that are currently in the profile
            is_currently_in_profile = server_name in current_servers
            server_choices.append(
                Choice(value=server_name, name=f"{server_name} ({command})", enabled=is_currently_in_profile)
            )

        # Clear any remaining command line arguments to avoid conflicts
        original_argv = sys.argv[:]
        sys.argv = [sys.argv[0]]  # Keep only script name

        try:
            # Get profile name first
            new_name = inquirer.text(
                message="Profile name:",
                default=profile_name,
                validate=lambda text: len(text.strip()) > 0,
                keybindings={"interrupt": [{"key": "escape"}]},  # Map ESC to interrupt
            ).execute()

            # Then get server selection with proper defaults
            selected_servers = inquirer.checkbox(
                message="Select servers to include in this profile:",
                choices=server_choices,
                keybindings={"interrupt": [{"key": "escape"}]},  # Map ESC to interrupt
            ).execute()

            answers = {"name": new_name, "servers": selected_servers}

        finally:
            # Restore original argv
            sys.argv = original_argv

        if not answers:
            return {"cancelled": True}

        return {
            "cancelled": False,
            "name": answers["name"].strip(),
            "servers": set(answers["servers"]),
        }

    except (KeyboardInterrupt, EOFError):
        return {"cancelled": True}
    except Exception as e:
        console.print(f"[red]Error running interactive form: {e}[/]")
        return None
