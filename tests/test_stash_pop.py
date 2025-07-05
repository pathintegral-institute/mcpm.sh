"""
Tests for deprecated stash/pop commands in MCPM v2.0

These commands have been removed and should show deprecation errors.
"""

from click.testing import CliRunner

from mcpm.cli import main


def test_stash_command_deprecated():
    """Test that stash command shows deprecation error"""
    runner = CliRunner()
    result = runner.invoke(main, ["stash", "test-server"])

    assert result.exit_code == 1
    assert "The 'mcpm stash' command has been removed in MCPM v2.0" in result.output
    assert "Use the new global configuration model instead" in result.output
    assert "mcpm install <server>" in result.output


def test_pop_command_deprecated():
    """Test that pop command shows deprecation error"""
    runner = CliRunner()
    result = runner.invoke(main, ["pop", "test-server"])

    assert result.exit_code == 1
    assert "The 'mcpm pop' command has been removed in MCPM v2.0" in result.output
    assert "Use the new global configuration model instead" in result.output
    assert "mcpm install <server>" in result.output


def test_mv_command_deprecated():
    """Test that mv command shows deprecation error"""
    runner = CliRunner()
    result = runner.invoke(main, ["mv", "src", "dest"])

    assert result.exit_code == 1
    assert "The 'mcpm mv' command has been removed in MCPM v2.0" in result.output
    assert "mcpm profile add <profile> <server>" in result.output


def test_cp_command_deprecated():
    """Test that cp command shows deprecation error"""
    runner = CliRunner()
    result = runner.invoke(main, ["cp", "src", "dest"])

    assert result.exit_code == 1
    assert "The 'mcpm cp' command has been removed in MCPM v2.0" in result.output
    assert "mcpm profile add <profile> <server>" in result.output


def test_target_command_deprecated():
    """Test that target command shows deprecation error"""
    runner = CliRunner()
    result = runner.invoke(main, ["target", "set", "@cursor"])

    assert result.exit_code == 1
    assert "The 'mcpm target' command has been removed in MCPM v2.0" in result.output
    assert "Use the new global configuration model instead" in result.output
