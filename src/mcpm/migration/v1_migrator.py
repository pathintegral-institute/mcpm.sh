"""
V1 to V2 Migration System
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from mcpm.core.schema import STDIOServerConfig
from mcpm.global_config import GlobalConfigManager
from mcpm.migration.v1_detector import V1ConfigDetector
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.config import DEFAULT_CONFIG_DIR, ConfigManager

logger = logging.getLogger(__name__)
console = Console()


class V1ToV2Migrator:
    """Handles migration from v1 to v2 configuration"""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = Path(config_dir) if config_dir else Path(DEFAULT_CONFIG_DIR)
        self.detector = V1ConfigDetector(self.config_dir)
        self.global_config = GlobalConfigManager()
        self.profile_config = ProfileConfigManager()
        self.config_manager = ConfigManager()

    def _wait_for_keypress(self, message: str):
        """Wait for any key press (cross-platform)"""
        import sys
        import termios
        import tty

        console.print(message, end="")

        try:
            # Unix/Linux/macOS
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except (ImportError, AttributeError):
            # Windows fallback - use input() which requires Enter
            input()

        console.print()  # Add newline after keypress

    def show_migration_prompt(self) -> str:
        """Show comprehensive migration prompt and get user consent"""
        console.print()

        # Welcome banner
        welcome_panel = Panel(
            "[bold cyan]🚀 Welcome to MCPM v2![/]\n\n"
            "We've detected v1 configuration files on your system.\n"
            "Let's help you migrate to the new and improved v2!",
            title="MCPM Migration Assistant",
            title_align="left",
            border_style="cyan",
            padding=(1, 2),
        )
        console.print(welcome_panel)
        console.print()

        # Analyze v1 config
        analysis = self.detector.analyze_v1_config()
        features = self.detector.detect_v1_features()

        # Show what we found
        self._show_v1_analysis(analysis, features)
        console.print()

        # Pause before showing v2 features
        self._wait_for_keypress("\n[dim]Press any key to learn about v2 improvements...[/]")
        console.print()

        # Show v2 improvements
        self._show_v2_improvements()
        console.print()

        # Pause before showing breaking changes
        self._wait_for_keypress("[dim]Press any key to review important changes...[/]")
        console.print()

        # Show breaking changes
        self._show_breaking_changes()
        console.print()

        # Get migration choice
        console.print("\n[bold yellow]What would you like to do with your v1 configuration?[/]")
        console.print("  [bold green]Y[/] - Migrate to v2 (recommended)")
        console.print("  [bold blue]N[/] - Start fresh with v2 (backup v1 configs)")
        console.print("  [bold red]I[/] - Ignore for now (continue with current command)")

        while True:
            choice = Prompt.ask(
                "Choose your option", choices=["y", "n", "i", "Y", "N", "I"], show_choices=False
            ).lower()

            if choice == "y":
                return "migrate"
            elif choice == "n":
                console.print("\n[blue]Starting fresh with v2 - your v1 configs will be safely backed up.[/]")
                return "start_fresh"
            elif choice == "i":
                console.print(
                    "\n[yellow]Continuing with current command. You can migrate later with 'mcpm migrate'.[/]"
                )
                console.print("[dim]Note: Some v2 features may not work properly with v1 configs.[/]")
                return "ignore"

    def start_fresh(self) -> bool:
        """Start fresh with v2 by backing up v1 configs without migration"""
        try:
            console.print("\n[bold cyan]🔄 Starting Fresh with v2[/]")

            # Create backups
            console.print("\n[bold]Creating backups of v1 configuration...[/]")
            backups = self.detector.backup_v1_configs()
            if backups:
                backup_dir = backups[0].parent
                console.print(f"  ✅ Backed up v1 configs to: [dim]{backup_dir}[/]")
                console.print(f"  📋 Created {len(backups)} backup files (including README)")

            # Clean up v1 configs
            console.print("\n[bold]Cleaning up v1 configuration files...[/]")
            self._cleanup_main_config()

            # Remove v1 profiles file if it exists
            if self.detector.profiles_file.exists():
                try:
                    self.detector.profiles_file.unlink()
                    console.print("  🧹 Removed v1 profiles.json")
                except Exception as e:
                    console.print(f"  ⚠️  Failed to remove profiles.json: {e}")

            # Show completion message
            fresh_start_panel = Panel(
                "[bold green]✅ Fresh Start Complete![/]\n\n"
                "🎯 [bold]What Happened[/]\n"
                "   • v1 configs safely backed up\n"
                "   • v1 files completely removed\n"
                "   • Ready for clean v2 experience\n\n"
                "🚀 [bold]Next Steps[/]\n"
                "   • Run [cyan]mcpm search[/] to find servers\n"
                "   • Use [cyan]mcpm install <server>[/] to add servers\n"
                "   • Create profiles with [cyan]mcpm profile create[/]\n"
                "   • Your v1 configs are in [cyan]~/.config/mcpm/backups/[/]",
                title="🆕 Fresh v2 Start",
                title_align="left",
                border_style="green",
                padding=(1, 2),
            )
            console.print(fresh_start_panel)

            return True

        except Exception as e:
            logger.error(f"Fresh start failed: {e}")
            console.print(f"\n[red]❌ Fresh start failed: {e}[/]")
            console.print("[yellow]Your v1 files are unchanged.[/]")
            return False

    def _show_v1_analysis(self, analysis: Dict, features: Dict[str, bool]):
        """Show analysis of current v1 configuration"""
        console.print("[bold]📋 Current Configuration Analysis[/]")

        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")

        # Config file
        if analysis["config_found"]:
            details = []
            if analysis["active_target"]:
                details.append(f"Active target: {analysis['active_target']}")
            if analysis["stashed_count"] > 0:
                details.append(f"{analysis['stashed_count']} stashed servers")
            if analysis["router_enabled"]:
                details.append("Router daemon configured")
            if analysis["share_active"]:
                details.append("Share session active")

            table.add_row("Main Config", "✅ Found", "\n".join(details) if details else "Basic configuration")
        else:
            table.add_row("Main Config", "❌ Not found", "")

        # Profiles
        if analysis["profiles_found"]:
            profile_details = []
            profile_details.append(f"{analysis['profile_count']} profiles")
            profile_details.append(f"{analysis['server_count']} total servers")
            for name, count in analysis["profiles"].items():
                profile_details.append(f"  • {name}: {count} servers")

            table.add_row("Profiles", "✅ Found", "\n".join(profile_details))
        else:
            table.add_row("Profiles", "❌ Not found", "")

        # Note: auth.json is a v2 feature, not v1, so we don't show it here

        console.print(table)

    def _show_v2_improvements(self):
        """Show v2 features and improvements"""
        improvements_panel = Panel(
            "[bold green]✨ What's New in v2[/]\n\n"
            "🎯 [bold]Simplified Architecture[/]\n"
            "   • Global server configuration - no more complex targets\n"
            "   • Virtual profiles as tags - easier organization\n"
            "   • Direct execution - no router daemon needed\n\n"
            "⚡ [bold]Better Performance[/]\n"
            "   • Faster startup - no daemon dependencies\n"
            "   • Direct stdio execution for MCP clients\n"
            "   • HTTP mode for testing and development\n\n"
            "🛠️ [bold]Enhanced Usability[/]\n"
            "   • Centralized server management with [cyan]mcpm ls[/]\n"
            "   • Easy profile management with [cyan]mcpm profile[/]\n"
            "   • Client integration with [cyan]mcpm client[/]\n"
            "   • Beautiful formatted output and logging\n\n"
            "🔧 [bold]Developer Experience[/]\n"
            "   • Inspector integration: [cyan]mcpm inspect[/]\n"
            "   • Local HTTP testing: [cyan]mcpm run --http[/]\n"
            "   • Public sharing: [cyan]mcpm share[/]\n"
            "   • Usage analytics: [cyan]mcpm usage[/]",
            title="🚀 MCPM v2 Features",
            title_align="left",
            border_style="green",
            padding=(1, 2),
        )
        console.print(improvements_panel)

    def _show_breaking_changes(self):
        """Show breaking changes from v1 to v2"""
        breaking_panel = Panel(
            "[bold red]⚠️ Breaking Changes[/]\n\n"
            "📋 [bold]Command Changes[/]\n"
            "   • [red]mcpm target[/] commands → [green]mcpm profile[/] commands\n"
            "   • [red]mcpm router[/] commands → [green]mcpm run --http[/] and [green]mcpm share[/]\n"
            "   • [red]mcpm stash/pop[/] commands → manual server management\n\n"
            "🎯 [bold]Configuration Changes[/]\n"
            "   • No more active targets - profiles are just tags\n"
            "   • No more stashed servers - enable/disable directly\n"
            "   • No more router daemon - direct execution\n\n"
            "🔄 [bold]Workflow Changes[/]\n"
            "   • Servers stored globally, tagged with profiles\n"
            "   • Clients managed independently\n"
            "   • Simplified sharing without router complexity",
            title="⚠️ Important Changes",
            title_align="left",
            border_style="yellow",
            padding=(1, 2),
        )
        console.print(breaking_panel)

    def migrate_config(self) -> bool:
        """Perform the full migration process"""
        try:
            console.print("\n[bold cyan]🔄 Starting Migration Process[/]")

            # Step 1: Create backups
            console.print("\n[bold]Step 1: Creating backups...[/]")
            backups = self.detector.backup_v1_configs()
            if backups:
                backup_dir = backups[0].parent
                console.print(f"  ✅ Backed up v1 configs to: [dim]{backup_dir}[/]")
                console.print(f"  📋 Created {len(backups)} backup files (including README)")

            # Step 2: Migrate profiles
            console.print("\n[bold]Step 2: Migrating profiles...[/]")
            migrated_profiles = self._migrate_profiles()

            # Step 3: Handle stashed servers
            console.print("\n[bold]Step 3: Processing stashed servers...[/]")
            self._handle_stashed_servers()

            # Step 4: Clean up main config
            console.print("\n[bold]Step 4: Cleaning up system configuration...[/]")
            self._cleanup_main_config()

            # Step 5: Show post-migration summary
            console.print("\n[bold]Step 5: Migration summary...[/]")
            self._show_migration_summary(migrated_profiles)

            # Step 6: Show next steps
            self._show_next_steps()

            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            console.print(f"\n[red]❌ Migration failed: {e}[/]")
            console.print("[yellow]Your original files are backed up and unchanged.[/]")
            return False

    def _migrate_profiles(self) -> Dict[str, int]:
        """Migrate v1 profiles to v2 virtual profiles"""
        profiles = self.detector.get_v1_profiles()
        migrated = {}

        for profile_name, servers in profiles.items():
            if not servers:  # Skip empty profiles
                console.print(f"  ⏭️  Skipping empty profile: [dim]{profile_name}[/]")
                continue

            console.print(f"  🔄 Migrating profile: [cyan]{profile_name}[/]")

            # Create virtual profile
            self.profile_config.create_profile(profile_name, description="Migrated from v1")
            server_count = 0

            for server_data in servers:
                try:
                    # Convert v1 server format to v2
                    server_config = self._convert_v1_server(server_data)

                    # Add to global config
                    if self.global_config.add_server(server_config):
                        # Tag with profile
                        self.profile_config.add_server_to_profile(profile_name, server_config.name)
                        server_count += 1
                        console.print(f"    ✅ Migrated: [green]{server_config.name}[/]")
                    else:
                        console.print(f"    ⚠️  Failed to add: [yellow]{server_data.get('name', 'unknown')}[/]")

                except Exception as e:
                    console.print(f"    ❌ Error migrating {server_data.get('name', 'unknown')}: {e}")

            migrated[profile_name] = server_count
            console.print(f"  ✅ Profile [cyan]{profile_name}[/] migrated with {server_count} servers")

        return migrated

    def _convert_v1_server(self, server_data: Dict) -> STDIOServerConfig:
        """Convert v1 server format to v2 STDIOServerConfig"""
        name = server_data.get("name", "unknown")

        # Handle different v1 server formats
        if "command" in server_data:
            # Command-based server (stdio)
            return STDIOServerConfig(
                name=name,
                command=server_data["command"],
                args=server_data.get("args", []),
                env=server_data.get("env", {}),
            )
        elif "url" in server_data:
            # URL-based server (SSE) - convert to npx command for typical MCP servers
            # This is a best-effort conversion
            console.print(f"    ⚠️  Converting URL-based server {name} to stdio format")
            return STDIOServerConfig(name=name, command="npx", args=["-y", f"@modelcontextprotocol/{name}"], env={})
        else:
            # Fallback
            return STDIOServerConfig(
                name=name, command="echo", args=[f"Migrated server {name} - please update command"], env={}
            )

    def _handle_stashed_servers(self):
        """Handle stashed servers from v1"""
        stashed = self.detector.get_stashed_servers()

        if not stashed:
            console.print("  ℹ️  No stashed servers found")
            return

        total_stashed = sum(len(servers) for servers in stashed.values())
        console.print(f"  📦 Found {total_stashed} stashed servers")

        # Ask user what to do with stashed servers
        action = Prompt.ask(
            "What would you like to do with stashed servers?",
            choices=["restore", "document", "skip"],
            default="document",
        )

        if action == "restore":
            self._restore_stashed_servers(stashed)
        elif action == "document":
            self._document_stashed_servers(stashed)
        else:
            console.print("  ⏭️  Skipping stashed servers")

    def _restore_stashed_servers(self, stashed: Dict):
        """Restore stashed servers to active configuration"""
        for scope, servers in stashed.items():
            console.print(f"  🔄 Restoring {len(servers)} servers from scope: [cyan]{scope}[/]")

            for server_name, server_data in servers.items():
                try:
                    server_config = self._convert_v1_server(server_data)
                    if self.global_config.add_server(server_config):
                        console.print(f"    ✅ Restored: [green]{server_name}[/]")
                    else:
                        console.print(f"    ⚠️  Failed to restore: [yellow]{server_name}[/]")
                except Exception as e:
                    console.print(f"    ❌ Error restoring {server_name}: {e}")

    def _document_stashed_servers(self, stashed: Dict):
        """Document stashed servers for user reference"""
        stashed_file = self.config_dir / "stashed_servers_v1_backup.json"

        try:
            with open(stashed_file, "w") as f:
                json.dump(stashed, f, indent=2)

            console.print(f"  📝 Stashed servers documented in: [dim]{stashed_file}[/]")
            console.print("  ℹ️  You can manually review and add these servers later using [cyan]mcpm add[/]")

        except IOError as e:
            console.print(f"  ❌ Failed to document stashed servers: {e}")

    def _cleanup_main_config(self):
        """Clean up main configuration file"""
        # Remove the entire config.json file since all v1 keys are outdated
        if self.detector.config_file.exists():
            try:
                self.detector.config_file.unlink()
                console.print("  🧹 Removed v1 config.json file")
            except Exception as e:
                console.print(f"  ⚠️  Failed to remove config.json: {e}")

        # Remove v1 profiles.json file after migration
        if self.detector.profiles_file.exists():
            try:
                self.detector.profiles_file.unlink()
                console.print("  🧹 Removed v1 profiles.json file")
            except Exception as e:
                console.print(f"  ⚠️  Failed to remove profiles.json: {e}")

    def _show_migration_summary(self, migrated_profiles: Dict[str, int]):
        """Show migration completion summary"""
        summary_panel = Panel(
            "[bold green]✅ Migration Completed Successfully![/]\n\n"
            f"📊 [bold]Migration Results[/]\n"
            f"   • {len(migrated_profiles)} profiles migrated\n"
            f"   • {sum(migrated_profiles.values())} servers migrated\n"
            f"   • v1 config.json and profiles.json removed\n"
            f"   • v1 configs backed up in [cyan]~/.config/mcpm/backups/[/]\n\n"
            f"🎯 [bold]What's Different Now[/]\n"
            f"   • All servers are in global configuration\n"
            f"   • Profiles are virtual tags for organization\n"
            f"   • Use [cyan]mcpm ls[/] to see all servers\n"
            f"   • Use [cyan]mcpm profile ls[/] to see profiles",
            title="🎉 Migration Complete",
            title_align="left",
            border_style="green",
            padding=(1, 2),
        )
        console.print(summary_panel)

    def _show_next_steps(self):
        """Show recommended next steps after migration"""
        next_steps_panel = Panel(
            "[bold cyan]📋 Recommended Next Steps[/]\n\n"
            "1️⃣  [bold]Verify Migration[/]\n"
            "   • Run [cyan]mcpm ls[/] to see your migrated servers\n"
            "   • Run [cyan]mcpm profile ls[/] to see your profiles\n"
            "   • Test a server: [cyan]mcpm run <server-name>[/]\n\n"
            "2️⃣  [bold]Import Client Configurations[/]\n"
            "   • Run [cyan]mcpm client ls[/] to see detected clients\n"
            "   • Import servers: [cyan]mcpm client edit <client>[/]\n"
            "   • Centralize your MCP management in MCPM\n\n"
            "3️⃣  [bold]Explore New Features[/]\n"
            "   • Try HTTP mode: [cyan]mcpm run --http <server>[/]\n"
            "   • Share publicly: [cyan]mcpm share <server>[/]\n"
            "   • Inspect servers: [cyan]mcpm inspect <server>[/]\n\n"
            "4️⃣  [bold]Access v1 Backups (If Needed)[/]\n"
            "   • v1 configs saved in [cyan]~/.config/mcpm/backups/[/]\n"
            "   • Review README.md in backup folder for guidance\n"
            "   • Update any scripts using old v1 commands",
            title="🚀 Next Steps",
            title_align="left",
            border_style="blue",
            padding=(1, 2),
        )
        console.print(next_steps_panel)

        # Show specific commands for their setup
        console.print("\n[bold]💡 Quick Start Commands for Your Setup:[/]")
        console.print("  [cyan]mcpm ls[/]                    # List all your servers")
        console.print("  [cyan]mcpm profile ls[/]           # List your migrated profiles")
        console.print("  [cyan]mcpm client ls[/]            # See detected MCP clients")
        console.print("  [cyan]mcpm --help[/]               # Explore all v2 commands")
        console.print()
