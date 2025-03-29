"""
Basic tests for MCPM
"""

from src.mcpm.cli import main


def test_cli_imports():
    """Test that the CLI can be imported"""
    assert main is not None
