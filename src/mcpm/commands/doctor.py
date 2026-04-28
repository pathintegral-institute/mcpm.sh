"""Doctor command for MCPM - System health check and diagnostics"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console

from mcpm.clients.client_registry import ClientRegistry
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.config import ConfigManager
from mcpm.utils.repository import RepositoryManager
from mcpm.utils.rich_click_config import click

console = Console()


@click.command()
@click.option("--json", "json_output", is_flag=True, help="Emit findings as JSON instead of human-readable Rich output.")
@click.help_option("-h", "--help")
def doctor(json_output: bool) -> None:
    """Check system health and installed server status.

    Performs comprehensive diagnostics of MCPM installation, configuration,
    and installed servers.

    Examples:
        mcpm doctor             # Run complete system health check (Rich text output)
        mcpm doctor --json      # Emit findings as JSON for programmatic consumption
    """
    findings = _collect_findings()
    if json_output:
        _render_json(findings)
    else:
        _render_text(findings)


def _collect_findings() -> Dict[str, Any]:
    """Run all diagnostic checks and return a structured findings dict.

    The returned dict's shape is part of the public `--json` contract: each
    top-level key (mcpm, python, node, config, cache, clients, profiles)
    holds the corresponding section's structured data, and `summary` rolls
    up the total `issues_found` count plus an `all_healthy` boolean. Adding
    a new top-level key is non-breaking; renaming or removing an existing
    one is a breaking change.
    """
    findings: Dict[str, Any] = {}
    findings["mcpm"] = _check_mcpm()
    findings["python"] = _check_python()
    findings["node"] = _check_node()
    findings["config"] = _check_config()
    findings["cache"] = _check_cache()
    findings["clients"] = _check_clients()
    findings["profiles"] = _check_profiles()
    issues_found = sum(int(section.get("issues", 0)) for section in findings.values())
    findings["summary"] = {"issues_found": issues_found, "all_healthy": issues_found == 0}
    return findings


def _check_mcpm() -> Dict[str, Any]:
    """Check MCPM installation. Returns version and any installation error."""
    try:
        from mcpm import __version__

        return {"version": __version__, "error": None, "issues": 0}
    except Exception as e:
        return {"version": None, "error": str(e), "issues": 1}


def _check_python() -> Dict[str, Any]:
    """Check Python environment. Always 0 issues — Python is always available."""
    return {"version": sys.version.split()[0], "executable": sys.executable, "issues": 0}


def _check_cli_tool_status(tool_name: str) -> Tuple[Optional[str], Optional[str], int]:
    """Return (version, error_message, issues_count) for a CLI tool on PATH.

    Helper for `_check_node()` so both `node` and `npm` get the same
    treatment without duplicating the subprocess + error-handling logic.
    """
    tool_path = shutil.which(tool_name)
    if not tool_path:
        return None, "not_found", 1
    try:
        version = subprocess.check_output([tool_path, "--version"], stderr=subprocess.DEVNULL).decode().strip()
        return version, None, 0
    except (subprocess.CalledProcessError, OSError):
        return None, "version_check_failed", 1


def _check_node() -> Dict[str, Any]:
    """Check Node.js + npm availability for `npx` server execution."""
    node_version, node_err, node_issues = _check_cli_tool_status("node")
    npm_version, npm_err, npm_issues = _check_cli_tool_status("npm")
    return {
        "node": {"version": node_version, "error": node_err},
        "npm": {"version": npm_version, "error": npm_err},
        "issues": node_issues + npm_issues,
    }


def _check_config() -> Dict[str, Any]:
    """Check MCPM configuration file."""
    try:
        config_manager = ConfigManager()
        config = config_manager.get_config()
        node_executable = config.get("node_executable")
        return {
            "config_file": config_manager.config_path,
            "node_executable": node_executable,
            "node_executable_set": bool(node_executable),
            "error": None,
            "issues": 0,
        }
    except Exception as e:
        return {
            "config_file": None,
            "node_executable": None,
            "node_executable_set": False,
            "error": str(e),
            "issues": 1,
        }


def _check_cache() -> Dict[str, Any]:
    """Check repository cache file presence + age."""
    try:
        import time

        repo_manager = RepositoryManager()
        cache_file = repo_manager.cache_file
        cache_exists = os.path.exists(cache_file)
        if not cache_exists:
            return {"cache_file": cache_file, "exists": False, "stale": False, "error": None, "issues": 0}
        cache_age = Path(cache_file).stat().st_mtime
        stale = (time.time() - cache_age) > 86400
        return {"cache_file": cache_file, "exists": True, "stale": stale, "error": None, "issues": 0}
    except Exception as e:
        return {"cache_file": None, "exists": False, "stale": False, "error": str(e), "issues": 1}


def _client_status_line(client: str) -> Optional[bool]:
    """Return True if installed, False if not, None on detection error."""
    try:
        client_manager = ClientRegistry.get_client_manager(client)
        if client_manager and client_manager.is_client_installed():
            return True
        return False
    except Exception:
        return None


def _check_clients() -> Dict[str, Any]:
    """Check supported MCP clients and which are installed locally."""
    try:
        clients = ClientRegistry.get_supported_clients()
        client_info = ClientRegistry.get_all_client_info()
        installed: List[str] = []
        not_installed: List[str] = []
        for client in clients:
            status = _client_status_line(client)
            if status:
                installed.append(client)
            else:
                not_installed.append(client)
        installed_display = [client_info.get(c, {}).get("name", c) for c in installed]
        not_installed_display = [client_info.get(c, {}).get("name", c) for c in not_installed]
        return {
            "supported_count": len(clients),
            "installed": installed,
            "installed_display": installed_display,
            "not_installed": not_installed,
            "not_installed_display": not_installed_display,
            "error": None,
            "issues": 0,
        }
    except Exception as e:
        return {
            "supported_count": 0,
            "installed": [],
            "installed_display": [],
            "not_installed": [],
            "not_installed_display": [],
            "error": str(e),
            "issues": 1,
        }


def _check_profiles() -> Dict[str, Any]:
    """Check configured profiles."""
    try:
        profile_manager = ProfileConfigManager()
        profiles = profile_manager.list_profiles()
        profile_names = list(profiles.keys()) if isinstance(profiles, dict) else list(profiles)
        return {"count": len(profile_names), "names": profile_names, "error": None, "issues": 0}
    except Exception as e:
        return {"count": 0, "names": [], "error": str(e), "issues": 1}


def _json_default(obj: Any) -> str:
    """Fallback for `json.dumps` — coerce PosixPath, Path, and other
    non-serializable values to strings so the JSON output is robust against
    upstream return shapes that mix `str` and `Path` for filesystem paths
    (e.g. `RepositoryManager.cache_file`).
    """
    return str(obj)


def _render_json(findings: Dict[str, Any]) -> None:
    """Emit findings as JSON to stdout. Pretty-printed with indent=2."""
    click.echo(json.dumps(findings, indent=2, default=_json_default))


def _render_text(findings: Dict[str, Any]) -> None:
    """Emit the existing Rich-formatted human-readable output.

    Reproduces the pre-`--json` output verbatim by reading from the
    structured findings dict instead of re-running the checks. Adding a
    new finding to `_collect_findings` requires a corresponding render
    block here — the JSON output drives the contract; text output is the
    human-friendly view.
    """
    console.print("[bold green]🩺 MCPM System Health Check[/]")
    console.print()
    _render_mcpm(findings["mcpm"])
    _render_python(findings["python"])
    _render_node(findings["node"])
    _render_config(findings["config"])
    _render_cache(findings["cache"])
    _render_clients(findings["clients"])
    _render_profiles(findings["profiles"])
    _render_summary(findings["summary"])


def _render_mcpm(section: Dict[str, Any]) -> None:
    console.print("[bold cyan]📦 MCPM Installation[/]")
    if section["error"]:
        console.print(f"  ❌ MCPM installation error: {section['error']}")
    else:
        console.print(f"  ✅ MCPM version: {section['version']}")


def _render_python(section: Dict[str, Any]) -> None:
    console.print("[bold cyan]🐍 Python Environment[/]")
    console.print(f"  ✅ Python version: {section['version']}")
    console.print(f"  ✅ Python executable: {section['executable']}")


def _render_node(section: Dict[str, Any]) -> None:
    console.print("[bold cyan]📊 Node.js Environment[/]")
    _render_cli_tool_line("Node.js", section["node"], "Node.js not found - npx servers will not work")
    _render_cli_tool_line("npm", section["npm"], "npm not found - package installation may fail")


def _render_cli_tool_line(display_name: str, info: Dict[str, Any], not_found_msg: str) -> None:
    if info["version"]:
        console.print(f"  ✅ {display_name} version: {info['version']}")
    elif info["error"] == "version_check_failed":
        console.print(f"  ⚠️  {display_name} found but failed to get version")
    else:
        console.print(f"  ⚠️  {not_found_msg}")


def _render_config(section: Dict[str, Any]) -> None:
    console.print("[bold cyan]⚙️  MCPM Configuration[/]")
    if section["error"]:
        console.print(f"  ❌ Configuration error: {section['error']}")
        return
    console.print(f"  ✅ Config file: {section['config_file']}")
    if section["node_executable"]:
        console.print(f"  ✅ Node executable: {section['node_executable']}")
    else:
        console.print("  ⚠️  No default node executable set")


def _render_cache(section: Dict[str, Any]) -> None:
    console.print("[bold cyan]📚 Repository Cache[/]")
    if section["error"]:
        console.print(f"  ❌ Cache check error: {section['error']}")
        return
    if not section["exists"]:
        console.print("  ⚠️  No cache file found - run 'mcpm search' to build cache")
        return
    console.print(f"  ✅ Cache file: {section['cache_file']}")
    if section["stale"]:
        console.print("  ⚠️  Cache is older than 24 hours - consider refreshing")


def _render_clients(section: Dict[str, Any]) -> None:
    console.print("[bold cyan]🖥️  Supported Clients[/]")
    if section["error"]:
        console.print(f"  ❌ Client check error: {section['error']}")
        return
    console.print(f"  ✅ {section['supported_count']} clients supported:")
    if section["installed_display"]:
        console.print(f"    ✅ Installed ({len(section['installed_display'])}): ", end="")
        console.print(", ".join(section["installed_display"]))
    if section["not_installed_display"]:
        not_installed = section["not_installed_display"]
        console.print(f"    ⚪ Available ({len(not_installed)}): ", end="")
        # Display first 3 + "and N more" suffix when truncating, matching
        # the pre-`--json` Rich output verbatim.
        display = list(not_installed[:3])
        if len(not_installed) > 3:
            display.append(f"and {len(not_installed) - 3} more")
        console.print(", ".join(display))
    if not section["installed_display"] and not section["not_installed_display"]:
        console.print("  ⚠️  No client information available")


def _render_profiles(section: Dict[str, Any]) -> None:
    console.print("[bold cyan]📁 Profiles[/]")
    if section["error"]:
        console.print(f"  ❌ Profile check error: {section['error']}")
        return
    console.print(f"  ✅ {section['count']} profiles configured")
    for profile in section["names"][:3]:
        console.print(f"    - {profile}")
    if section["count"] > 3:
        console.print(f"    ... and {section['count'] - 3} more")


def _render_summary(summary: Dict[str, Any]) -> None:
    console.print()
    if summary["all_healthy"]:
        console.print("[bold green]✅ All systems healthy! No issues found.[/]")
    else:
        console.print(f"[bold yellow]⚠️  {summary['issues_found']} issue(s) detected.[/]")
        console.print()
        console.print("[italic]Suggestions:[/]")
        console.print("  • Run 'mcpm config set' to configure node executable")
        console.print("  • Run 'mcpm search' to build repository cache")
        console.print("  • Install Node.js for npx server support")
    console.print()
    console.print("[italic]For more help, visit: https://github.com/pathintegral-institute/mcpm.sh[/]")
