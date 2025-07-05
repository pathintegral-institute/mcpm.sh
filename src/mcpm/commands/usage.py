"""Enhanced usage command for MCPM - Display analytics using SQLite"""

import asyncio
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mcpm.monitor import get_monitor
from mcpm.utils.rich_click_config import click

console = Console()


async def get_usage_stats_async(days: int, server_name: str = None, profile_name: str = None):
    """Get usage statistics from DuckDB asynchronously"""
    monitor = await get_monitor()

    try:
        if server_name:
            return await monitor.get_server_stats(server_name, days)
        elif profile_name:
            return await monitor.get_profile_stats(profile_name, days)
        else:
            # Try to use computed stats, fallback to legacy if needed
            try:
                return await monitor.get_computed_usage_stats(days)
            except AttributeError:
                # Fallback to legacy method if get_computed_usage_stats doesn't exist
                return await monitor.get_usage_stats(days)
    finally:
        await monitor.close()


@click.command()
@click.option("--days", "-d", default=30, help="Show usage for last N days")
@click.option("--server", "-s", help="Show usage for specific server")
@click.option("--profile", "-p", help="Show usage for specific profile")
@click.help_option("-h", "--help")
def usage(days, server, profile):
    """Display comprehensive analytics and usage data.

    Shows detailed usage statistics including run counts, session data,
    performance metrics, and activity patterns for servers and profiles.
    Data is stored in SQLite for efficient querying and analysis.

    Examples:
        mcpm usage                    # Show all usage for last 30 days
        mcpm usage --days 7           # Show usage for last 7 days
        mcpm usage --server browse    # Show usage for specific server
        mcpm usage --profile web-dev  # Show usage for specific profile
    """
    console.print(f"[bold green]📊 MCPM Usage Analytics[/] [dim](last {days} days)[/]")
    console.print()

    try:
        # Run async function in event loop
        if server:
            stats = asyncio.run(get_usage_stats_async(days, server_name=server))
            show_server_usage(stats, server)
        elif profile:
            stats = asyncio.run(get_usage_stats_async(days, profile_name=profile))
            show_profile_usage(stats, profile)
        else:
            stats = asyncio.run(get_usage_stats_async(days))
            show_usage_overview(stats, days)

    except Exception as e:
        console.print(f"[red]Error retrieving usage data: {e}[/]")
        console.print("[dim]Make sure the SQLite database is accessible.[/]")


def show_server_usage(stats, server_name: str):
    """Show detailed usage for a specific server."""
    if not stats:
        console.print(f"[yellow]No usage data found for server '[bold]{server_name}[/]'[/]")
        console.print("[dim]Usage data is collected when servers are run via 'mcpm run'[/]")
        return

    # Create origin breakdown text
    origin_text = ""
    if stats.origin_breakdown:
        origin_items = []
        for origin, count in stats.origin_breakdown.items():
            origin_items.append(f"{origin}: {count}")
        origin_text = f"\n[green]Request Origins:[/] {', '.join(origin_items)}"

    # Create server info panel
    server_panel = Panel(
        f"[bold cyan]Server:[/] {stats.server_name}\n\n"
        f"[green]Total Sessions:[/] {stats.total_sessions:,}\n"
        f"[green]Total Runs:[/] {stats.total_runs:,}\n"
        f"[green]Primary Transport:[/] {stats.primary_transport}\n"
        f"[green]Success Rate:[/] {stats.success_rate:.1f}%\n"
        f"[green]Total Runtime:[/] {format_duration(stats.total_duration_ms)}\n\n"
        f"[green]First Used:[/] {format_timestamp(stats.first_used)}\n"
        f"[green]Last Used:[/] {format_timestamp(stats.last_used)}"
        f"{origin_text}",
        title="📈 Server Statistics",
        title_align="left",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(server_panel)


def show_profile_usage(stats, profile_name: str):
    """Show detailed usage for a specific profile."""
    if not stats:
        console.print(f"[yellow]No usage data found for profile '[bold]{profile_name}[/]'[/]")
        console.print("[dim]Usage data is collected when profiles are run via 'mcpm profile run'[/]")
        return

    # Create profile info panel
    profile_panel = Panel(
        f"[bold cyan]Profile:[/] {stats.profile_name}\n\n"
        f"[green]Total Sessions:[/] {stats.total_sessions:,}\n"
        f"[green]Total Runs:[/] {stats.total_runs:,}\n"
        f"[green]Server Count:[/] {stats.server_count}\n\n"
        f"[green]First Used:[/] {format_timestamp(stats.first_used)}\n"
        f"[green]Last Used:[/] {format_timestamp(stats.last_used)}",
        title="📁 Profile Statistics",
        title_align="left",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(profile_panel)


def show_usage_overview(stats, days: int):
    """Show comprehensive usage overview."""
    if not stats.servers and not stats.profiles and not stats.recent_sessions:
        console.print("[yellow]No usage data available yet.[/]")
        console.print("[dim]Usage data is collected automatically when servers are used via MCPM.[/]")
        console.print("[dim]Try running: [cyan]mcpm run <server-name>[/] to generate some data.[/]")
        return

    # Summary panel
    summary_panel = Panel(
        f"[bold green]📊 Summary[/]\n\n"
        f"[cyan]Active Servers:[/] {stats.total_servers:,}\n"
        f"[cyan]Active Profiles:[/] {stats.total_profiles:,}\n"
        f"[cyan]Total Sessions:[/] {stats.total_sessions:,}\n"
        f"[cyan]Analysis Period:[/] {stats.date_range_days} days",
        title="🎯 Overview",
        title_align="left",
        border_style="green",
        padding=(1, 2),
    )
    console.print(summary_panel)
    console.print()

    # Server usage table
    if stats.servers:
        console.print("[bold cyan]📈 Server Usage[/]")

        server_table = Table()
        server_table.add_column("Server", style="cyan")
        server_table.add_column("Sessions", justify="right")
        server_table.add_column("Transport", style="green")
        server_table.add_column("Success Rate", justify="right")
        server_table.add_column("Runtime", justify="right")
        server_table.add_column("Last Used", style="dim")

        for server in stats.servers:
            # Get transport info from metadata (we'll add this to server stats)
            transport = getattr(server, "primary_transport", "unknown")

            server_table.add_row(
                server.server_name,
                f"{server.total_sessions:,}",
                transport,
                f"{server.success_rate:.1f}%",
                format_duration(server.total_duration_ms),
                format_timestamp(server.last_used, short=True),
            )

        console.print(server_table)
        console.print()

    # Profile usage table
    if stats.profiles:
        console.print("[bold cyan]📁 Profile Usage[/]")

        profile_table = Table()
        profile_table.add_column("Profile", style="cyan")
        profile_table.add_column("Sessions", justify="right")
        profile_table.add_column("Runs", justify="right")
        profile_table.add_column("Servers", justify="right")
        profile_table.add_column("Last Used", style="dim")

        for profile in stats.profiles:
            profile_table.add_row(
                profile.profile_name,
                f"{profile.total_sessions:,}",
                f"{profile.total_runs:,}",
                f"{profile.server_count}",
                format_timestamp(profile.last_used, short=True),
            )

        console.print(profile_table)
        console.print()

    # Recent activity
    if stats.recent_sessions:
        console.print("[bold cyan]🕒 Recent Activity[/]")

        activity_table = Table()
        activity_table.add_column("Time", style="dim")
        activity_table.add_column("Action", style="green")
        activity_table.add_column("Target", style="cyan")
        activity_table.add_column("Duration", justify="right")
        activity_table.add_column("Status")

        for session in stats.recent_sessions[:10]:  # Show last 10 sessions
            target = session.server_name or session.profile_name or "Unknown"
            status = "✅" if session.success else "❌"

            activity_table.add_row(
                format_timestamp(session.timestamp, short=True),
                session.action,
                target,
                format_duration(session.duration_ms),
                status,
            )

        console.print(activity_table)
        console.print()

    # Usage patterns summary
    if stats.recent_sessions:
        action_counts = {}
        origin_counts = {}
        transport_counts = {}

        for session in stats.recent_sessions:
            action = session.action
            action_counts[action] = action_counts.get(action, 0) + 1

            # Extract origin and transport from metadata if available
            if session.metadata:
                # Handle both legacy format (nested) and new computed format (direct)
                if "computed_from_events" in session.metadata:
                    # New computed format - data is directly in metadata
                    origin = session.metadata.get("source", "unknown")
                    transport = session.metadata.get("transport", "unknown")
                else:
                    # Legacy format - data is nested in client_info/server_info
                    client_info = session.metadata.get("client_info", {})
                    server_info = session.metadata.get("server_info", {})
                    origin = client_info.get("origin", "unknown")
                    transport = server_info.get("transport") or client_info.get("transport", "unknown")

                origin_counts[origin] = origin_counts.get(origin, 0) + 1
                transport_counts[transport] = transport_counts.get(transport, 0) + 1

        console.print("[bold cyan]📋 Activity Breakdown[/]")
        for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  [green]{action}:[/] {count} operations")

        if origin_counts:
            console.print("\n[bold cyan]🌐 Request Origins[/]")
            for origin, count in sorted(origin_counts.items(), key=lambda x: x[1], reverse=True):
                console.print(f"  [blue]{origin}:[/] {count} requests")

        if transport_counts:
            console.print("\n[bold cyan]🚀 Transport Types[/]")
            for transport, count in sorted(transport_counts.items(), key=lambda x: x[1], reverse=True):
                console.print(f"  [magenta]{transport}:[/] {count} sessions")


def format_duration(duration_ms):
    """Format duration in milliseconds to human readable format"""
    if not duration_ms:
        return "N/A"

    if duration_ms < 1000:
        return f"{duration_ms}ms"
    elif duration_ms < 60000:
        return f"{duration_ms / 1000:.1f}s"
    elif duration_ms < 3600000:
        return f"{duration_ms / 60000:.1f}m"
    else:
        return f"{duration_ms / 3600000:.1f}h"


def format_timestamp(timestamp_str, short=False):
    """Format timestamp string to human readable format"""
    if not timestamp_str:
        return "Never"

    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        if short:
            return dt.strftime("%m-%d %H:%M")
        else:
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return timestamp_str
