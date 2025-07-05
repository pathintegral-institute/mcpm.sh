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
        assert "mcpm install" in result.output
        assert "mcpm run" in result.output


def test_legacy_commands_exist_but_deprecated():
    """Test that legacy commands exist but show deprecation"""
    runner = CliRunner()

    # Test that legacy add/rm still work (aliases)
    result = runner.invoke(main, ["add", "--help"])
    assert result.exit_code == 0

    result = runner.invoke(main, ["rm", "--help"])
    assert result.exit_code == 0

    # Test that deprecated commands show errors
    deprecated_commands = ["stash", "pop", "mv", "cp", "target"]

    for cmd in deprecated_commands:
        result = runner.invoke(main, [cmd, "--help"])
        # Deprecated commands should either fail or show error
        if result.exit_code == 0:
            # If help works, the actual command should fail
            result = runner.invoke(main, [cmd, "test"])
            assert result.exit_code == 1
            assert "removed in MCPM v2.0" in result.output
