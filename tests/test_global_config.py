"""
Tests for MCPM v2.0 Global Configuration Model
"""

import tempfile
from pathlib import Path

from click.testing import CliRunner

from mcpm.cli import main
from mcpm.global_config import GlobalConfigManager


def test_global_config_manager():
    """Test basic GlobalConfigManager functionality"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "servers.json"
        manager = GlobalConfigManager(config_path=str(config_path))

        # Test empty config
        assert manager.list_servers() == {}
        assert not manager.server_exists("test-server")
        assert manager.get_server("test-server") is None

        # Test adding servers would require server config objects
        # For now, just test the basic structure works
        servers = manager.list_servers()
        assert isinstance(servers, dict)


def test_list_shows_global_config():
    """Test that mcpm ls shows global configuration"""
    runner = CliRunner()
    result = runner.invoke(main, ["ls"])

    assert result.exit_code == 0
    assert "MCPM Global Configuration" in result.output
    assert "global configuration" in result.output.lower()


def test_v2_help_shows_global_model():
    """Test that help shows v2.0 global configuration messaging"""
    from unittest.mock import patch

    # Mock v1 config detection to avoid migration prompt
    with patch("mcpm.cli.V1ConfigDetector.has_v1_config", return_value=False):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "global configuration" in result.output.lower()
        assert "profile" in result.output.lower()
        assert "install" in result.output
        assert "run" in result.output


def test_deprecated_commands_removed():
    """Test that deprecated commands have been completely removed"""
    runner = CliRunner()

    # Test that deprecated commands no longer exist
    deprecated_commands = ["stash", "pop", "mv", "cp", "target", "add", "rm"]

    for cmd in deprecated_commands:
        result = runner.invoke(main, [cmd, "--help"])
        assert result.exit_code == 2  # Click's "No such command" exit code
        assert f"No such command '{cmd}'" in result.output
