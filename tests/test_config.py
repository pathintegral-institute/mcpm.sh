"""
Tests for the config command
"""

import json
import tempfile
from unittest.mock import Mock, patch

from click.testing import CliRunner

from mcpm.commands.config import set as config_set
from mcpm.utils.config import ConfigManager


def test_config_set_non_interactive_success(monkeypatch):
    """Test successful non-interactive config set."""
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({}, f)

    # Mock ConfigManager
    mock_config_manager = Mock(spec=ConfigManager)
    mock_config_manager.set_config.return_value = True

    with patch("mcpm.commands.config.ConfigManager", return_value=mock_config_manager):
        # Force non-interactive mode
        monkeypatch.setattr("mcpm.commands.config.is_non_interactive", lambda: True)

        runner = CliRunner()
        result = runner.invoke(config_set, ["--key", "node_executable", "--value", "npx"])

        assert result.exit_code == 0
        assert "Configuration 'node_executable' set to 'npx'" in result.output
        mock_config_manager.set_config.assert_called_once_with("node_executable", "npx")


def test_config_set_non_interactive_invalid_key(monkeypatch):
    """Test non-interactive config set with invalid key."""
    mock_config_manager = Mock(spec=ConfigManager)

    with patch("mcpm.commands.config.ConfigManager", return_value=mock_config_manager):
        # Force non-interactive mode
        monkeypatch.setattr("mcpm.commands.config.is_non_interactive", lambda: True)

        runner = CliRunner()
        result = runner.invoke(config_set, ["--key", "invalid_key", "--value", "test"])

        assert result.exit_code == 1
        assert "Unknown configuration key 'invalid_key'" in result.output
        assert "Supported keys:" in result.output
        assert "node_executable" in result.output


def test_config_set_non_interactive_invalid_value(monkeypatch):
    """Test non-interactive config set with invalid value."""
    mock_config_manager = Mock(spec=ConfigManager)

    with patch("mcpm.commands.config.ConfigManager", return_value=mock_config_manager):
        # Force non-interactive mode
        monkeypatch.setattr("mcpm.commands.config.is_non_interactive", lambda: True)

        runner = CliRunner()
        result = runner.invoke(config_set, ["--key", "node_executable", "--value", "invalid_executable"])

        assert result.exit_code == 1
        assert "Invalid value 'invalid_executable' for key 'node_executable'" in result.output
        assert "Valid values for 'node_executable':" in result.output
        assert "npx" in result.output


def test_config_set_non_interactive_missing_parameters(monkeypatch):
    """Test non-interactive config set with missing parameters."""
    mock_config_manager = Mock(spec=ConfigManager)

    with patch("mcpm.commands.config.ConfigManager", return_value=mock_config_manager):
        # Force non-interactive mode
        monkeypatch.setattr("mcpm.commands.config.is_non_interactive", lambda: True)

        runner = CliRunner()

        # Test missing value
        result = runner.invoke(config_set, ["--key", "node_executable"])
        assert result.exit_code == 1
        assert "Both --key and --value are required in non-interactive mode" in result.output

        # Test missing key
        result = runner.invoke(config_set, ["--value", "npx"])
        assert result.exit_code == 1
        assert "Both --key and --value are required in non-interactive mode" in result.output


def test_config_set_with_force_flag(monkeypatch):
    """Test config set with --force flag triggering non-interactive mode."""
    mock_config_manager = Mock(spec=ConfigManager)
    mock_config_manager.set_config.return_value = True

    with patch("mcpm.commands.config.ConfigManager", return_value=mock_config_manager):
        # Don't force non-interactive mode, but use --force flag
        monkeypatch.setattr("mcpm.commands.config.is_non_interactive", lambda: False)
        monkeypatch.setattr("mcpm.commands.config.should_force_operation", lambda: False)

        runner = CliRunner()
        result = runner.invoke(config_set, ["--key", "node_executable", "--value", "bunx", "--force"])

        assert result.exit_code == 0
        assert "Configuration 'node_executable' set to 'bunx'" in result.output
        mock_config_manager.set_config.assert_called_once_with("node_executable", "bunx")


def test_config_set_interactive_fallback(monkeypatch):
    """Test config set falls back to interactive mode when no CLI params provided."""
    mock_config_manager = Mock(spec=ConfigManager)
    mock_config_manager.set_config.return_value = True

    with patch("mcpm.commands.config.ConfigManager", return_value=mock_config_manager):
        # Force interactive mode
        monkeypatch.setattr("mcpm.commands.config.is_non_interactive", lambda: False)
        monkeypatch.setattr("mcpm.commands.config.should_force_operation", lambda: False)

        # Mock the interactive prompts
        with patch("mcpm.commands.config.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["node_executable", "npx"]

            runner = CliRunner()
            result = runner.invoke(config_set, [])

            assert result.exit_code == 0
            assert "Default node executable set to: npx" in result.output
            mock_config_manager.set_config.assert_called_once_with("node_executable", "npx")


def test_config_set_help():
    """Test the config set command help output."""
    runner = CliRunner()
    result = runner.invoke(config_set, ["--help"])

    assert result.exit_code == 0
    assert "Set MCPM configuration" in result.output
    assert "Interactive by default, or use CLI parameters for automation" in result.output
    assert "--key" in result.output
    assert "--value" in result.output
    assert "--force" in result.output


def test_config_set_all_valid_node_executables(monkeypatch):
    """Test config set with all valid node executable values."""
    mock_config_manager = Mock(spec=ConfigManager)
    mock_config_manager.set_config.return_value = True

    valid_executables = ["npx", "bunx", "pnpm dlx", "yarn dlx"]

    with patch("mcpm.commands.config.ConfigManager", return_value=mock_config_manager):
        # Force non-interactive mode
        monkeypatch.setattr("mcpm.commands.config.is_non_interactive", lambda: True)

        runner = CliRunner()

        for executable in valid_executables:
            result = runner.invoke(config_set, ["--key", "node_executable", "--value", executable])
            assert result.exit_code == 0
            assert f"Configuration 'node_executable' set to '{executable}'" in result.output
