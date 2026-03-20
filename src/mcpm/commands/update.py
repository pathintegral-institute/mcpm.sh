"""
Update command — check for and apply updates to installed MCP servers.

Usage:
    mcpm update                     # Update all servers
    mcpm update codeforward-odoo    # Update a specific server
    mcpm update --check             # Dry run — check only
    mcpm update --init              # Populate source metadata for existing servers
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.prompt import Confirm

from mcpm.core.schema import STDIOServerConfig
from mcpm.core.source import (
    GithubReleaseSource,
    GitSource,
    NpxSource,
    RemoteSource,
    SourcesManager,
    UnknownSource,
    UvxSource,
    detect_source,
)
from mcpm.global_config import GlobalConfigManager
from mcpm.utils import git as git_utils
from mcpm.utils.non_interactive import is_non_interactive, should_force_operation
from mcpm.utils.rich_click_config import click

console = Console()
err_console = Console(stderr=True)
logger = logging.getLogger(__name__)


# --- Init subcommand ---


@click.command(name="update", context_settings=dict(help_option_names=["-h", "--help"]))
@click.argument("server_name", required=False)
@click.option("--check", "--dry-run", "-c", "check_only", is_flag=True, help="Check for updates only, don't apply them")
@click.option("--rebase", is_flag=True, help="Use git pull --rebase instead of --ff-only")
@click.option("--force", is_flag=True, help="Skip confirmation prompts")
@click.option("--verbose", "-V", is_flag=True, help="Show detailed output")
@click.option("--init", "run_init", is_flag=True, help="Scan installed servers and populate source metadata")
def update(server_name, check_only, rebase, force, verbose, run_init):
    """Check for and apply updates to installed MCP servers.

    Updates git-based servers by pulling the latest changes from their remote.
    NPX/UVX servers auto-update at runtime and are shown for informational purposes.
    HTTP remote servers are skipped.

    Examples:

    \b
        mcpm update                          # Update all servers
        mcpm update codeforward-odoo         # Update one server
        mcpm update --check                  # Dry run
        mcpm update --rebase                 # Use rebase instead of ff-only
        mcpm update --init                   # Set up source metadata
        mcpm update --init --force           # Re-detect all sources
    """
    if run_init:
        _run_init(force=force)
        return

    _run_update(
        server_name=server_name,
        check_only=check_only,
        use_rebase=rebase,
        force=force,
        verbose=verbose,
    )


# --- Init implementation ---


def _run_init(force: bool = False):
    """Scan all installed servers and populate source metadata."""
    global_config = GlobalConfigManager()
    sources = SourcesManager()
    servers = global_config.list_servers()

    if not servers:
        console.print("[yellow]No servers found in global configuration.[/]")
        return

    console.print(f"[bold]Scanning {len(servers)} server(s) for source metadata...[/]\n")

    created = 0
    skipped = 0
    updated = 0

    for name, server_config in servers.items():
        existing = sources.get(name)

        if existing and not force:
            label = _source_type_label(existing)
            console.print(f"  [dim]{name}[/]  [dim]{label}[/]  [dim]already configured, skipping[/]")
            skipped += 1
            continue

        # Auto-detect source type
        detected = detect_source(server_config)

        # For git sources, enrich with remote info and prompt for post_update
        if isinstance(detected, GitSource):
            repo_path = Path(detected.path)
            if repo_path.exists() and git_utils.is_git_repo(repo_path):
                detected.remote_url = git_utils.get_remote_url(repo_path)
                detected.branch = git_utils.get_default_branch(repo_path)

                console.print(f"  [cyan]{name}[/]  [green]git[/]  {detected.path}")
                if detected.remote_url:
                    console.print(f"    remote: {detected.remote_url}")
                if detected.branch:
                    console.print(f"    branch: {detected.branch}")

                # Prompt for post_update command
                post_update = _suggest_post_update(repo_path)
                if not is_non_interactive():
                    if post_update:
                        console.print(f"    [dim]detected build system, suggested post_update:[/] [cyan]{post_update}[/]")
                        user_input = click.prompt(
                            "    post_update command (enter to accept, 'none' to skip)",
                            default=post_update,
                            show_default=False,
                        )
                        if user_input.lower() != "none":
                            detected.post_update = user_input
                    else:
                        user_input = click.prompt(
                            "    post_update command (optional, enter to skip)",
                            default="",
                            show_default=False,
                        )
                        if user_input:
                            detected.post_update = user_input
                elif post_update:
                    detected.post_update = post_update
            else:
                console.print(f"  [cyan]{name}[/]  [yellow]git[/]  path not found: {detected.path}")

        elif isinstance(detected, NpxSource):
            console.print(f"  [cyan]{name}[/]  [blue]npx[/]  {detected.package}")

        elif isinstance(detected, UvxSource):
            console.print(f"  [cyan]{name}[/]  [blue]uvx[/]  {detected.package}")

        elif isinstance(detected, RemoteSource):
            if isinstance(server_config, STDIOServerConfig):
                console.print(f"  [cyan]{name}[/]  [dim]remote[/]")
            else:
                console.print(f"  [cyan]{name}[/]  [dim]remote[/]  {getattr(server_config, 'url', '')}")

        elif isinstance(detected, UnknownSource):
            console.print(f"  [cyan]{name}[/]  [yellow]unknown[/]  {detected.reason}")

        else:
            console.print(f"  [cyan]{name}[/]  [dim]{detected.type}[/]")

        sources.set(name, detected)
        if existing:
            updated += 1
        else:
            created += 1

    console.print(f"\n[bold green]Done.[/] {created} created, {updated} updated, {skipped} skipped.")


def _suggest_post_update(repo_path: Path) -> Optional[str]:
    """Suggest a post_update command based on files in the repo."""
    if (repo_path / "pyproject.toml").exists():
        if (repo_path / "uv.lock").exists():
            return "uv sync"
        # Default to uv for Python projects — mcpm standardizes on uv
        return "uv sync"

    if (repo_path / "package.json").exists():
        # Check for build script
        try:
            with open(repo_path / "package.json", "r", encoding="utf-8") as f:
                pkg = json.load(f)
            scripts = pkg.get("scripts", {})
            if "build" in scripts:
                return "npm install && npm run build"
            return "npm install"
        except (json.JSONDecodeError, OSError):
            return "npm install"

    if (repo_path / "go.mod").exists():
        return "go build ./..."

    return None


# --- Update implementation ---


def _run_update(
    server_name: Optional[str] = None,
    check_only: bool = False,
    use_rebase: bool = False,
    force: bool = False,
    verbose: bool = False,
):
    """Main update logic — check and optionally apply updates."""
    global_config = GlobalConfigManager()
    sources = SourcesManager()
    servers = global_config.list_servers()

    if not servers:
        console.print("[yellow]No servers found in global configuration.[/]")
        return

    # Filter to specific server if requested
    if server_name:
        if server_name not in servers:
            console.print(f"[bold red]Error:[/] Server '{server_name}' not found.")
            return
        servers = {server_name: servers[server_name]}

    console.print("[bold]Checking for updates...[/]\n")

    # Phase 1: Check all servers
    updatable = []  # List of (name, source, status) tuples for servers that can be updated
    git_checked = 0  # Git servers successfully checked (including up-to-date)
    git_skipped = 0  # Git servers skipped (dirty, auth failed, path missing, etc.)

    for name, server_config in servers.items():
        source = sources.get(name)

        if not source:
            console.print(f"  [cyan]{name:<22}[/] [yellow]???[/]     no source metadata — run [bold]mcpm update --init[/]")
            continue

        if isinstance(source, NpxSource):
            console.print(f"  [cyan]{name:<22}[/] [blue]npx[/]     auto-updates via npx ({source.package})")
            continue

        if isinstance(source, UvxSource):
            console.print(f"  [cyan]{name:<22}[/] [blue]uvx[/]     auto-updates via uvx ({source.package})")
            continue

        if isinstance(source, RemoteSource):
            console.print(f"  [cyan]{name:<22}[/] [dim]remote[/]  skipped")
            continue

        if isinstance(source, GithubReleaseSource):
            console.print(f"  [cyan]{name:<22}[/] [dim]release[/] skipped (v2)")
            continue

        if isinstance(source, UnknownSource):
            if verbose:
                console.print(f"  [cyan]{name:<22}[/] [dim]unknown[/] {source.reason}")
            continue

        if isinstance(source, GitSource):
            checked = _check_git_server(name, source, sources, updatable, verbose)
            if checked:
                git_checked += 1
            else:
                git_skipped += 1

    # Phase 2: Apply updates if not check-only
    if not updatable:
        if git_checked > 0 and git_skipped == 0:
            console.print("\n[green]All servers are up to date.[/]")
        elif git_checked > 0 and git_skipped > 0:
            console.print(f"\n[green]All checked servers are up to date.[/] ({git_skipped} skipped)")
        elif git_skipped > 0:
            console.print(f"\n[yellow]No servers could be checked.[/] ({git_skipped} skipped)")
        else:
            console.print("\n[yellow]No updatable servers found.[/] Run [bold]mcpm update --init[/] to set up source metadata.")
        return

    if check_only:
        console.print(f"\n[bold]{len(updatable)} server(s) have updates available.[/]")
        return

    # Confirm
    if not force and not should_force_operation() and not is_non_interactive():
        if not Confirm.ask(f"\n{len(updatable)} server(s) have updates available. Apply?"):
            console.print("[yellow]Cancelled.[/]")
            return

    console.print()

    # Apply updates
    success_count = 0
    for name, source, status in updatable:
        console.print(f"[bold]Updating {name}...[/]")
        repo_path = Path(source.path)

        # Pull
        if use_rebase:
            result = git_utils.pull_rebase(repo_path)
        else:
            result = git_utils.pull_ff_only(repo_path)

        if not result.success:
            console.print(f"  git pull [red]✗[/] {result.error}")
            if not use_rebase and "cannot fast-forward" in (result.error or ""):
                console.print(f"  [dim]Run manually: cd {source.path} && git pull --rebase[/]")
            console.print()
            continue

        console.print(f"  git pull [green]✓[/] ({status.commits_behind} new commit{'s' if status.commits_behind != 1 else ''})")

        # Post-update command
        post_ok = True
        if source.post_update:
            post_ok = _run_post_update(source.post_update, repo_path)
            if not post_ok:
                console.print(f"  [dim]Run manually: cd {source.path} && {source.post_update}[/]")

        if post_ok:
            sources.mark_updated(name)
            success_count += 1

        console.print()

    console.print(f"[bold green]Done.[/] {success_count} server(s) updated.")


def _check_git_server(name, source, sources, updatable, verbose) -> bool:
    """Check a single git server for updates. Returns True if successfully checked."""
    repo_path = Path(source.path)

    # Path exists?
    if not repo_path.exists():
        console.print(f"  [cyan]{name:<22}[/] [red]git[/]     path not found: {source.path}")
        return False

    # Dirty?
    if git_utils.is_dirty(repo_path):
        console.print(f"  [cyan]{name:<22}[/] [yellow]git[/]     skipped (uncommitted changes)")
        return False

    # Fetch
    fetch_result = git_utils.fetch(repo_path)
    if not fetch_result.success:
        console.print(f"  [cyan]{name:<22}[/] [red]git[/]     skipped ({fetch_result.error})")
        return False

    sources.mark_checked(name)

    # Compare
    status = git_utils.check_status(repo_path, branch=source.branch)
    if status.error:
        console.print(f"  [cyan]{name:<22}[/] [red]git[/]     error: {status.error}")
        return False

    if status.commits_behind == 0:
        console.print(f"  [cyan]{name:<22}[/] [green]git[/]     up to date")
        return True

    # Has updates
    plural = "s" if status.commits_behind != 1 else ""
    console.print(
        f"  [cyan]{name:<22}[/] [yellow]git[/]     "
        f"[bold]{status.commits_behind} commit{plural} behind {status.remote_branch}[/]"
    )
    if verbose and status.commit_summaries:
        for summary in status.commit_summaries:
            console.print(f"    [dim]{summary}[/]")

    updatable.append((name, source, status))
    return True


def _run_post_update(command: str, cwd: Path) -> bool:
    """Run a post-update command in the given directory."""
    console.print(f"  {command} ", end="")
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            console.print("[green]✓[/]")
            return True
        else:
            console.print("[red]✗[/]")
            console.print(f"  [red]Error:[/] {result.stderr.strip()[:200]}")
            return False
    except subprocess.TimeoutExpired:
        console.print("[red]✗[/] (timed out after 120s)")
        return False
    except Exception as e:
        console.print(f"[red]✗[/] ({e})")
        return False


def _source_type_label(source) -> str:
    """Get a display label for a source type."""
    if isinstance(source, GitSource):
        return "git"
    if isinstance(source, GithubReleaseSource):
        return "release"
    if isinstance(source, NpxSource):
        return "npx"
    if isinstance(source, UvxSource):
        return "uvx"
    if isinstance(source, RemoteSource):
        return "remote"
    if isinstance(source, UnknownSource):
        return "unknown"
    return source.type
