"""
Tests for the 'info' command
"""

from unittest.mock import Mock

from click.testing import CliRunner

from mcpm.commands.info import info


def test_info_basic(monkeypatch):
    """Test basic functionality of the info command"""
    # Mock repository manager
    mock_repo_manager = Mock()
    mock_repo_manager.get_server_metadata = Mock(
        return_value={
            "name": "test-server",
            "display_name": "Test Server",
            "description": "A test server for unit tests",
            "license": "MIT",
            "author": {"name": "Test Author", "email": "test@example.com"},
            "categories": ["test"],
            "tags": ["example", "testing"],
        }
    )
    monkeypatch.setattr("mcpm.commands.info.repo_manager", mock_repo_manager)

    # Run the command
    runner = CliRunner()
    result = runner.invoke(info, ["test-server"])

    # Check expected output
    assert result.exit_code == 0
    assert "Showing information for MCP server: test-server" in result.output
    assert "Test Server" in result.output
    assert "A test server for unit tests" in result.output
    assert "Test Author" in result.output
    assert "MIT" in result.output
    mock_repo_manager.get_server_metadata.assert_called_once_with("test-server")


def test_info_not_found(monkeypatch):
    """Test info command with a non-existent server"""
    # Mock repository manager
    mock_repo_manager = Mock()
    mock_repo_manager.get_server_metadata = Mock(return_value=None)
    monkeypatch.setattr("mcpm.commands.info.repo_manager", mock_repo_manager)

    # Run the command
    runner = CliRunner()
    result = runner.invoke(info, ["nonexistent"])

    # Check expected output
    assert result.exit_code == 0
    assert "Showing information for MCP server: nonexistent" in result.output
    assert "Server 'nonexistent' not found." in result.output
    mock_repo_manager.get_server_metadata.assert_called_once_with("nonexistent")


def test_info_error_handling(monkeypatch):
    """Test error handling during info command execution"""
    # Mock repository manager to raise an exception
    mock_repo_manager = Mock()
    mock_repo_manager.get_server_metadata = Mock(side_effect=Exception("Test error"))
    monkeypatch.setattr("mcpm.commands.info.repo_manager", mock_repo_manager)

    # Run the command
    runner = CliRunner()
    result = runner.invoke(info, ["test-server"])

    # Check expected output
    assert result.exit_code == 0
    assert "Error: Error retrieving information for server 'test-server'" in result.output
    assert "Test error" in result.output
    mock_repo_manager.get_server_metadata.assert_called_once_with("test-server")


def test_info_comprehensive(monkeypatch):
    """Test info command with a server that has comprehensive details"""
    # Mock repository manager
    mock_repo_manager = Mock()
    mock_repo_manager.get_server_metadata = Mock(
        return_value={
            "name": "comprehensive-server",
            "display_name": "Comprehensive Server",
            "description": "A server with comprehensive details",
            "repository": {"type": "git", "url": "https://github.com/example/comprehensive-server"},
            "homepage": "https://example.com/comprehensive-server",
            "documentation": "https://docs.example.com/comprehensive-server",
            "license": "Apache-2.0",
            "author": {
                "name": "Comprehensive Author",
                "email": "author@example.com",
                "url": "https://author.example.com",
            },
            "categories": ["test", "comprehensive"],
            "tags": ["example", "testing", "comprehensive"],
            "installations": {
                "npm": {
                    "type": "npm",
                    "description": "NPM installation",
                    "recommended": True,
                    "command": "npx",
                    "args": ["-y", "comprehensive-package"],
                    "dependencies": ["dep1", "dep2"],
                    "env": {"API_KEY": "${API_KEY}"},
                },
                "docker": {
                    "type": "docker",
                    "description": "Docker installation",
                    "command": "docker",
                    "args": ["run", "comprehensive-server"],
                    "env": {"DOCKER_ENV": "value"},
                },
            },
            "examples": [
                {"title": "Example 1", "description": "First example", "prompt": "Use the comprehensive server"},
                {"title": "Example 2", "description": "Second example", "code": "server.connect()"},
            ],
        }
    )
    monkeypatch.setattr("mcpm.commands.info.repo_manager", mock_repo_manager)

    # Run the command
    runner = CliRunner()
    result = runner.invoke(info, ["comprehensive-server"])

    # Check expected output
    assert result.exit_code == 0
    assert "Comprehensive Server" in result.output
    assert "A server with comprehensive details" in result.output

    # Check URLs section
    assert "URLs:" in result.output
    assert "Repository: https://github.com/example/comprehensive-server" in result.output
    assert "Homepage: https://example.com/comprehensive-server" in result.output
    assert "Documentation: https://docs.example.com/comprehensive-server" in result.output
    assert "Author URL: https://author.example.com" in result.output

    # Check Installation Details
    assert "Installation Details:" in result.output
    assert "npm: NPM installation" in result.output
    assert "docker: Docker installation" in result.output
    assert "Command: npx -y comprehensive-package" in result.output
    assert "Dependencies: dep1, dep2" in result.output
    assert "API_KEY" in result.output

    # Check Examples
    assert "Examples:" in result.output
    assert "Example 1" in result.output
    assert "First example" in result.output
    assert "Use the comprehensive server" in result.output
    assert "Example 2" in result.output
    assert "server.connect()" in result.output

    mock_repo_manager.get_server_metadata.assert_called_once_with("comprehensive-server")
