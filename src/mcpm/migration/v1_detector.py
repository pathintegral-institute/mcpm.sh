"""
V1 Configuration Detection and Analysis
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from mcpm.utils.config import DEFAULT_CONFIG_DIR

logger = logging.getLogger(__name__)


class V1ConfigDetector:
    """Detects and analyzes v1 configuration files"""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = Path(config_dir) if config_dir else Path(DEFAULT_CONFIG_DIR)
        self.config_file = self.config_dir / "config.json"
        self.profiles_file = self.config_dir / "profiles.json"

    def has_v1_config(self) -> bool:
        """Check if v1 configuration files exist with actual v1 content"""
        # Check for legacy profiles file (clear indicator of v1)
        if self.profiles_file.exists():
            return True

        # Check config file for v1-specific content
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)

                # Look for v1-specific content (not just the keys with None values)
                v1_indicators = [
                    config.get("active_client"),
                    config.get("active_target"),
                    config.get("stashed_servers"),
                    config.get("router"),
                    config.get("share"),
                ]

                # Return True if any v1 indicator has actual content (not None/empty)
                return any(indicator for indicator in v1_indicators)

            except (json.JSONDecodeError, IOError):
                pass

        return False

    def detect_v1_features(self) -> Dict[str, bool]:
        """Detect which v1 features are present in the config"""
        features = {
            "active_target": False,
            "stashed_servers": False,
            "router_config": False,
            "share_status": False,
            "legacy_profiles": False,
        }

        # Check main config file
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)

                # Check for actual v1 content, not just the presence of keys with null values
                features["active_target"] = any(config.get(key) for key in ["active_client", "active_target"])
                features["stashed_servers"] = bool(config.get("stashed_servers"))
                features["router_config"] = bool(config.get("router"))
                features["share_status"] = bool(config.get("share"))

            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to read v1 config file: {e}")

        # Check profiles file
        if self.profiles_file.exists():
            features["legacy_profiles"] = True

        return features

    def analyze_v1_config(self) -> Dict[str, any]:
        """Analyze v1 configuration and return migration info"""
        analysis = {
            "config_found": False,
            "profiles_found": False,
            "server_count": 0,
            "profile_count": 0,
            "stashed_count": 0,
            "active_target": None,
            "router_enabled": False,
            "share_active": False,
            "profiles": {},
            "clients_with_stashed": [],
        }

        # Analyze main config
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)

                analysis["config_found"] = True
                analysis["active_target"] = config.get("active_target")
                analysis["router_enabled"] = bool(config.get("router"))
                share_config = config.get("share", {})
                analysis["share_active"] = bool(share_config and share_config.get("url"))

                # Count stashed servers
                stashed = config.get("stashed_servers", {}) or {}
                analysis["stashed_count"] = sum(len(servers) for servers in stashed.values())
                analysis["clients_with_stashed"] = list(stashed.keys())

            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to analyze v1 config file: {e}")

        # Analyze profiles
        if self.profiles_file.exists():
            try:
                with open(self.profiles_file) as f:
                    profiles = json.load(f)

                analysis["profiles_found"] = True
                analysis["profile_count"] = len(profiles)
                analysis["profiles"] = {name: len(servers) for name, servers in profiles.items()}
                analysis["server_count"] = sum(analysis["profiles"].values())

            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to analyze v1 profiles file: {e}")

        return analysis

    def get_v1_profiles(self) -> Dict[str, List[Dict]]:
        """Get v1 profiles for migration"""
        if not self.profiles_file.exists():
            return {}

        try:
            with open(self.profiles_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read v1 profiles: {e}")
            return {}

    def get_stashed_servers(self) -> Dict[str, Dict[str, Dict]]:
        """Get stashed servers for migration"""
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file) as f:
                config = json.load(f)
            return config.get("stashed_servers", {})
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read stashed servers: {e}")
            return {}

    def backup_v1_configs(self) -> List[Path]:
        """Create backups of v1 config files in system backup directory"""
        import shutil
        from datetime import datetime

        # Create backup directory with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.config_dir / "backups" / f"v1_migration_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        backed_up = []

        for config_file in [self.config_file, self.profiles_file]:
            if config_file.exists():
                backup_path = backup_dir / config_file.name
                try:
                    shutil.copy2(config_file, backup_path)
                    backed_up.append(backup_path)
                    logger.info(f"Backed up {config_file} to {backup_path}")
                except IOError as e:
                    logger.error(f"Failed to backup {config_file}: {e}")

        # Create a README file explaining the backup
        readme_path = backup_dir / "README.md"
        try:
            with open(readme_path, "w") as f:
                f.write(f"""# MCPM v1 Configuration Backup

This directory contains your MCPM v1 configuration files that were automatically backed up during migration to v2.

**Backup Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Files Backed Up

- `config.json`: Main v1 configuration (active targets, stashed servers, router settings)
- `profiles.json`: v1 profile definitions (if existed)

## Restoring from Backup

If you need to restore any v1 settings:

1. **Manual Review**: Open the JSON files to see your old configuration
2. **Individual Settings**: Copy specific values you need back to v2 config
3. **Full Restore**: Replace current config files with these backups (not recommended)

## v1 vs v2 Differences

- **Active Targets**: No longer needed - use profiles as tags instead
- **Stashed Servers**: Managed directly - enable/disable servers as needed
- **Router Daemon**: Replaced with direct execution and sharing features

## Support

If you need help understanding or migrating specific v1 settings:
- Run `mcpm --help` to see v2 commands
- Visit: https://github.com/pathintegral-institute/mcpm.sh/issues
""")
            backed_up.append(readme_path)
        except IOError as e:
            logger.warning(f"Failed to create backup README: {e}")

        return backed_up
