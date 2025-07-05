"""
Tests for MCPM v1 to v2 migration system
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mcpm.migration import V1ConfigDetector, V1ToV2Migrator


@pytest.fixture
def temp_config_dir():
    """Create a temporary config directory for testing"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def v1_config_files(temp_config_dir):
    """Create sample v1 config files"""
    # Main config with v1 features
    config_data = {
        "active_client": "claude-desktop",
        "active_target": "%web-dev",
        "stashed_servers": {
            "claude-desktop": {
                "test-server": {"name": "test-server", "command": "npx", "args": ["-y", "test-server"], "env": {}}
            }
        },
        "router": {"host": "localhost", "port": 6276, "api_key": "test-key"},
        "share": {"url": "https://test.mcpm.sh/sse", "pid": 12345},
    }

    config_file = temp_config_dir / "config.json"
    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=2)

    # Profiles file
    profiles_data = {
        "web-dev": [
            {
                "name": "mcp-server-browse",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-browse"],
                "env": {},
            },
            {
                "name": "mcp-server-git",
                "command": "python",
                "args": ["-m", "mcp.server.git"],
                "env": {"PATH": "/usr/bin"},
            },
        ],
        "data-science": [{"name": "pandas-server", "url": "http://localhost:8080/sse", "headers": {}}],
    }

    profiles_file = temp_config_dir / "profiles.json"
    with open(profiles_file, "w") as f:
        json.dump(profiles_data, f, indent=2)

    # Auth file (should be preserved)
    auth_data = {"api_key": "test-auth-key"}
    auth_file = temp_config_dir / "auth.json"
    with open(auth_file, "w") as f:
        json.dump(auth_data, f, indent=2)

    return {"config": config_file, "profiles": profiles_file, "auth": auth_file}


def test_v1_config_detection(temp_config_dir, v1_config_files):
    """Test v1 configuration detection"""
    detector = V1ConfigDetector(temp_config_dir)

    # Should detect v1 config
    assert detector.has_v1_config()

    # Should detect all v1 features (auth_config is not a v1 feature)
    features = detector.detect_v1_features()
    assert features["active_target"]
    assert features["stashed_servers"]
    assert features["router_config"]
    assert features["share_status"]
    assert features["legacy_profiles"]


def test_v1_config_analysis(temp_config_dir, v1_config_files):
    """Test v1 configuration analysis"""
    detector = V1ConfigDetector(temp_config_dir)
    analysis = detector.analyze_v1_config()

    assert analysis["config_found"]
    assert analysis["profiles_found"]
    assert analysis["active_target"] == "%web-dev"
    assert analysis["router_enabled"]
    assert analysis["share_active"]
    assert analysis["stashed_count"] == 1
    assert analysis["profile_count"] == 2
    assert analysis["server_count"] == 3  # 2 in web-dev + 1 in data-science
    assert "claude-desktop" in analysis["clients_with_stashed"]


def test_backup_creation(temp_config_dir, v1_config_files):
    """Test backup file creation"""
    detector = V1ConfigDetector(temp_config_dir)
    backups = detector.backup_v1_configs()

    assert len(backups) == 3  # config, profiles, README

    # Check backup files exist in timestamped directory
    backup_dir = backups[0].parent
    assert backup_dir.exists()
    assert "v1_migration_" in backup_dir.name

    # Check all expected files are backed up
    backup_names = [backup.name for backup in backups]
    assert "config.json" in backup_names
    assert "profiles.json" in backup_names
    assert "README.md" in backup_names

    # Check README exists and has content
    readme_path = backup_dir / "README.md"
    assert readme_path.exists()
    with open(readme_path) as f:
        readme_content = f.read()
        assert "MCPM v1 Configuration Backup" in readme_content
        assert "Backup Date:" in readme_content


def test_migration_without_interaction(temp_config_dir, v1_config_files):
    """Test migration logic without user interaction"""
    # Mock user interactions to avoid prompts during testing
    with (
        patch(
            "mcpm.migration.v1_migrator.Prompt.ask", side_effect=["y", "document"]
        ),  # First for migration choice, second for stashed servers
        patch("mcpm.migration.v1_migrator.console.print"),
        patch("mcpm.migration.v1_migrator.V1ToV2Migrator._wait_for_keypress"),  # Mock keypress waits
    ):
        migrator = V1ToV2Migrator(temp_config_dir)

        # Test migration components individually
        detector = migrator.detector

        # Should detect v1 config
        assert detector.has_v1_config()

        # Should be able to get profiles
        profiles = detector.get_v1_profiles()
        assert "web-dev" in profiles
        assert "data-science" in profiles
        assert len(profiles["web-dev"]) == 2

        # Should be able to get stashed servers
        stashed = detector.get_stashed_servers()
        assert "claude-desktop" in stashed
        assert "test-server" in stashed["claude-desktop"]


def test_no_v1_config(temp_config_dir):
    """Test behavior when no v1 config exists"""
    detector = V1ConfigDetector(temp_config_dir)

    # Should not detect v1 config
    assert not detector.has_v1_config()

    # Features should all be false
    features = detector.detect_v1_features()
    assert not any(features.values())

    # Analysis should show nothing found
    analysis = detector.analyze_v1_config()
    assert not analysis["config_found"]
    assert not analysis["profiles_found"]
    assert analysis["server_count"] == 0
    assert analysis["profile_count"] == 0


def test_migration_command_import():
    """Test that migration command can be imported"""
    from mcpm.commands.migrate import migrate

    assert migrate is not None


def test_start_fresh_functionality(temp_config_dir, v1_config_files):
    """Test start fresh functionality"""
    migrator = V1ToV2Migrator(temp_config_dir)

    # Verify v1 files exist before start fresh
    assert migrator.detector.config_file.exists()
    assert migrator.detector.profiles_file.exists()

    # Run start fresh
    success = migrator.start_fresh()
    assert success

    # Verify backup was created
    backup_dirs = list((temp_config_dir / "backups").glob("v1_migration_*"))
    assert len(backup_dirs) == 1
    backup_dir = backup_dirs[0]
    assert (backup_dir / "config.json").exists()
    assert (backup_dir / "profiles.json").exists()
    assert (backup_dir / "README.md").exists()
    # auth.json should not be backed up since it's a v2 feature
    assert not (backup_dir / "auth.json").exists()

    # Verify v1 files are cleaned up (both profiles and config removed)
    assert not migrator.detector.profiles_file.exists()
    assert not migrator.detector.config_file.exists()


def test_cli_integration():
    """Test that CLI includes migration command"""
    from mcpm.cli import main

    # Check that migrate command is registered
    assert "migrate" in [cmd.name for cmd in main.commands.values()]
