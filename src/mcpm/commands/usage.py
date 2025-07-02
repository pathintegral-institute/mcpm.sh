"""Usage command for MCPM - Display analytics and usage data"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.config import ConfigManager

console = Console()


def get_usage_data_file():
    """Get path to usage data file."""
    config_manager = ConfigManager()
    config_dir = Path(config_manager.config_dir)
    return config_dir / "usage_data.json"


def load_usage_data():
    """Load usage data from file."""
    usage_file = get_usage_data_file()
    if not usage_file.exists():
        return {"servers": {}, "profiles": {}, "sessions": []}
    
    try:
        with open(usage_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"servers": {}, "profiles": {}, "sessions": []}


def save_usage_data(data):
    """Save usage data to file."""
    usage_file = get_usage_data_file()
    usage_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(usage_file, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError:
        pass  # Fail silently for usage tracking


def record_server_usage(server_name, action="run"):
    """Record server usage event."""
    data = load_usage_data()
    
    # Initialize server data if not exists
    if server_name not in data["servers"]:
        data["servers"][server_name] = {
            "total_runs": 0,
            "last_used": None,
            "first_used": None,
            "total_runtime": 0
        }
    
    # Update server stats
    now = datetime.now().isoformat()
    server_data = data["servers"][server_name]
    
    if action == "run":
        server_data["total_runs"] += 1
        server_data["last_used"] = now
        if not server_data["first_used"]:
            server_data["first_used"] = now
    
    # Record session
    data["sessions"].append({
        "server": server_name,
        "action": action,
        "timestamp": now
    })
    
    # Keep only last 1000 sessions
    if len(data["sessions"]) > 1000:
        data["sessions"] = data["sessions"][-1000:]
    
    save_usage_data(data)


def record_profile_usage(profile_name, action="run"):
    """Record profile usage event."""
    data = load_usage_data()
    
    # Initialize profile data if not exists
    if profile_name not in data["profiles"]:
        data["profiles"][profile_name] = {
            "total_runs": 0,
            "last_used": None,
            "first_used": None
        }
    
    # Update profile stats
    now = datetime.now().isoformat()
    profile_data = data["profiles"][profile_name]
    
    if action == "run":
        profile_data["total_runs"] += 1
        profile_data["last_used"] = now
        if not profile_data["first_used"]:
            profile_data["first_used"] = now
    
    save_usage_data(data)


@click.command()
@click.option("--days", "-d", default=30, help="Show usage for last N days")
@click.option("--server", "-s", help="Show usage for specific server")
@click.option("--profile", "-p", help="Show usage for specific profile")
@click.help_option("-h", "--help")
def usage(days, server, profile):
    """Display analytics and usage data for servers.
    
    Shows usage statistics including run counts, last usage times,
    and activity patterns for servers and profiles.
    
    Examples:
        mcpm usage                    # Show all usage for last 30 days
        mcpm usage --days 7           # Show usage for last 7 days  
        mcpm usage --server browse    # Show usage for specific server
        mcpm usage --profile web-dev  # Show usage for specific profile
    """
    console.print(f"[bold green]📊 MCPM Usage Analytics[/] [dim](last {days} days)[/]")
    console.print()
    
    # Load usage data
    data = load_usage_data()
    
    if not data["servers"] and not data["profiles"]:
        console.print("[yellow]No usage data available yet.[/]")
        console.print("[dim]Usage data is collected when servers are run via 'mcpm run'[/]")
        return
    
    # Calculate date threshold
    threshold = datetime.now() - timedelta(days=days)
    
    # Filter sessions by date
    recent_sessions = []
    for session in data["sessions"]:
        try:
            session_date = datetime.fromisoformat(session["timestamp"])
            if session_date >= threshold:
                recent_sessions.append(session)
        except ValueError:
            continue
    
    # Show server-specific usage
    if server:
        show_server_usage(data, server, recent_sessions)
        return
    
    # Show profile-specific usage  
    if profile:
        show_profile_usage(data, profile, recent_sessions)
        return
    
    # Show overview
    show_usage_overview(data, recent_sessions, days)


def show_server_usage(data, server_name, recent_sessions):
    """Show detailed usage for a specific server."""
    if server_name not in data["servers"]:
        console.print(f"[yellow]No usage data found for server '[bold]{server_name}[/]'[/]")
        return
    
    server_data = data["servers"][server_name]
    
    console.print(f"[bold cyan]Server: {server_name}[/]")
    console.print()
    
    # Basic stats
    console.print(f"[green]Total runs:[/] {server_data['total_runs']}")
    
    if server_data['last_used']:
        last_used = datetime.fromisoformat(server_data['last_used'])
        console.print(f"[green]Last used:[/] {last_used.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if server_data['first_used']:
        first_used = datetime.fromisoformat(server_data['first_used'])
        console.print(f"[green]First used:[/] {first_used.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Recent activity
    server_sessions = [s for s in recent_sessions if s["server"] == server_name]
    if server_sessions:
        console.print()
        console.print(f"[green]Recent activity:[/] {len(server_sessions)} sessions")


def show_profile_usage(data, profile_name, recent_sessions):
    """Show detailed usage for a specific profile."""
    if profile_name not in data["profiles"]:
        console.print(f"[yellow]No usage data found for profile '[bold]{profile_name}[/]'[/]")
        return
    
    profile_data = data["profiles"][profile_name]
    
    console.print(f"[bold cyan]Profile: {profile_name}[/]")
    console.print()
    
    # Basic stats
    console.print(f"[green]Total runs:[/] {profile_data['total_runs']}")
    
    if profile_data['last_used']:
        last_used = datetime.fromisoformat(profile_data['last_used'])
        console.print(f"[green]Last used:[/] {last_used.strftime('%Y-%m-%d %H:%M:%S')}")


def show_usage_overview(data, recent_sessions, days):
    """Show overall usage overview."""
    # Server usage table
    if data["servers"]:
        console.print("[bold cyan]📈 Server Usage[/]")
        
        server_table = Table()
        server_table.add_column("Server", style="cyan")
        server_table.add_column("Total Runs", justify="right")
        server_table.add_column("Last Used", style="dim")
        
        # Sort servers by total runs
        sorted_servers = sorted(
            data["servers"].items(), 
            key=lambda x: x[1]["total_runs"], 
            reverse=True
        )
        
        for server_name, server_data in sorted_servers:
            last_used = "Never"
            if server_data["last_used"]:
                try:
                    last_used_dt = datetime.fromisoformat(server_data["last_used"])
                    last_used = last_used_dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass
            
            server_table.add_row(
                server_name,
                str(server_data["total_runs"]),
                last_used
            )
        
        console.print(server_table)
        console.print()
    
    # Profile usage table
    if data["profiles"]:
        console.print("[bold cyan]📁 Profile Usage[/]")
        
        profile_table = Table()
        profile_table.add_column("Profile", style="cyan")
        profile_table.add_column("Total Runs", justify="right")
        profile_table.add_column("Last Used", style="dim")
        
        # Sort profiles by total runs
        sorted_profiles = sorted(
            data["profiles"].items(),
            key=lambda x: x[1]["total_runs"],
            reverse=True
        )
        
        for profile_name, profile_data in sorted_profiles:
            last_used = "Never"
            if profile_data["last_used"]:
                try:
                    last_used_dt = datetime.fromisoformat(profile_data["last_used"])
                    last_used = last_used_dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass
            
            profile_table.add_row(
                profile_name,
                str(profile_data["total_runs"]),
                last_used
            )
        
        console.print(profile_table)
        console.print()
    
    # Recent activity summary
    if recent_sessions:
        console.print("[bold cyan]🕒 Recent Activity[/]")
        console.print(f"  {len(recent_sessions)} sessions in last {days} days")
        
        # Group by action
        actions = {}
        for session in recent_sessions:
            action = session.get("action", "run")
            actions[action] = actions.get(action, 0) + 1
        
        for action, count in actions.items():
            console.print(f"  {count} {action} operations")
        
        console.print()
    
    # Summary
    total_servers = len([s for s in data["servers"].values() if s["total_runs"] > 0])
    total_profiles = len([p for p in data["profiles"].values() if p["total_runs"] > 0])
    total_runs = sum(s["total_runs"] for s in data["servers"].values())
    
    console.print(f"[bold green]Summary:[/] {total_servers} servers, {total_profiles} profiles, {total_runs} total runs")