from unittest.mock import Mock

from click.testing import CliRunner

from mcpm.commands.search import search


def test_search_all_servers(monkeypatch):
    """Test searching for all servers without a query"""
    # Mock repository manager
    mock_repo_manager = Mock()
    mock_repo_manager.search_servers = Mock(
        return_value=[
            {
                "name": "server1",
                "display_name": "Server One",
                "description": "First test server",
                "categories": ["category1"],
                "tags": ["tag1", "tag2"],
            },
            {
                "name": "server2",
                "display_name": "Server Two",
                "description": "Second test server",
                "categories": ["category2"],
                "tags": ["tag3"],
            },
        ]
    )
    monkeypatch.setattr("mcpm.commands.search.repo_manager", mock_repo_manager)

    # Run the command
    runner = CliRunner()
    result = runner.invoke(search, [])

    assert result.exit_code == 0
    assert "Listing all available MCP servers" in result.output
    assert "server1" in result.output
    assert "server2" in result.output
    assert "Found 2 server(s) matching search criteria" in result.output
    mock_repo_manager.search_servers.assert_called_once_with(None)


def test_search_with_query(monkeypatch):
    """Test searching with a specific query"""
    # Mock repository manager
    mock_repo_manager = Mock()
    mock_repo_manager.search_servers = Mock(
        return_value=[
            {
                "name": "github-server",
                "display_name": "GitHub Server",
                "description": "GitHub integration server",
                "categories": ["integration"],
                "tags": ["github", "api"],
            }
        ]
    )
    monkeypatch.setattr("mcpm.commands.search.repo_manager", mock_repo_manager)

    # Run the command
    runner = CliRunner()
    result = runner.invoke(search, ["github"])

    assert result.exit_code == 0
    assert "Searching for MCP servers matching 'github'" in result.output
    assert "github-server" in result.output
    assert "Found 1 server(s) matching search criteria" in result.output
    mock_repo_manager.search_servers.assert_called_once_with("github")


def test_search_no_results(monkeypatch):
    """Test searching with no results"""
    # Mock repository manager
    mock_repo_manager = Mock()
    mock_repo_manager.search_servers = Mock(return_value=[])
    monkeypatch.setattr("mcpm.commands.search.repo_manager", mock_repo_manager)

    # Run the command
    runner = CliRunner()
    result = runner.invoke(search, ["nonexistent"])

    assert result.exit_code == 0
    assert "Searching for MCP servers matching 'nonexistent'" in result.output
    assert "No matching MCP servers found" in result.output
    mock_repo_manager.search_servers.assert_called_once_with("nonexistent")


def test_search_table_view(monkeypatch):
    """Test searching with table view"""
    # Mock repository manager
    mock_repo_manager = Mock()
    mock_repo_manager.search_servers = Mock(
        return_value=[
            {
                "name": "test-server",
                "display_name": "Test Server",
                "description": "A test server",
                "categories": ["test"],
                "tags": ["example"],
                "license": "MIT",
                "author": {"name": "Test Author", "email": "test@example.com"},
                "installation": {"package": "test-package"},
                "installations": {
                    "npm": {
                        "type": "npm",
                        "description": "NPM installation",
                        "recommended": True,
                        "command": "npx",
                        "args": ["-y", "test-package"],
                        "dependencies": ["dependency1"],
                        "env": {"API_KEY": "${API_KEY}"},
                    }
                },
                "examples": [{"title": "Example Usage", "description": "How to use this server"}],
            }
        ]
    )
    monkeypatch.setattr("mcpm.commands.search.repo_manager", mock_repo_manager)

    # Run the command with table flag
    runner = CliRunner()
    result = runner.invoke(search, ["--table"])

    assert result.exit_code == 0
    assert "Test Server" in result.output
    assert "A test server" in result.output
    # Table output won't have these detailed sections that were in the detailed view
    # assert "Server Information:" in result.output
    # assert "Installation Details:" in result.output
    # assert "Example:" in result.output
    assert "Found 1 server(s) matching search criteria" in result.output
    mock_repo_manager.search_servers.assert_called_once_with(None)


def test_search_error_handling(monkeypatch):
    """Test error handling during search"""
    # Mock repository manager to raise an exception
    mock_repo_manager = Mock()
    mock_repo_manager.search_servers = Mock(side_effect=Exception("Test error"))
    monkeypatch.setattr("mcpm.commands.search.repo_manager", mock_repo_manager)

    # Run the command
    runner = CliRunner()
    result = runner.invoke(search, [])

    assert result.exit_code == 0
    assert "Error: Error searching for servers" in result.output
    assert "Test error" in result.output
    mock_repo_manager.search_servers.assert_called_once_with(None)


def test_search_with_query_and_table(monkeypatch):
    """Test searching with both a query and table view"""
    # Mock repository manager
    mock_repo_manager = Mock()
    mock_repo_manager.search_servers = Mock(
        return_value=[
            {
                "name": "test-server",
                "display_name": "Test Server",
                "description": "A test server",
                "categories": ["test"],
                "tags": ["example"],
                "license": "MIT",
                "author": {"name": "Test Author", "email": "test@example.com"},
                "installation": {"package": "test-package"},
                "installations": {
                    "npm": {
                        "type": "npm",
                        "description": "NPM installation",
                        "recommended": True,
                        "command": "npx",
                        "args": ["-y", "test-package"],
                        "dependencies": ["dependency1"],
                        "env": {"API_KEY": "${API_KEY}"},
                    }
                },
                "examples": [{"title": "Example Usage", "description": "How to use this server"}],
            }
        ]
    )
    monkeypatch.setattr("mcpm.commands.search.repo_manager", mock_repo_manager)

    # Run the command with both query and table flag
    runner = CliRunner()
    result = runner.invoke(search, ["test", "--table"])

    assert result.exit_code == 0
    assert "Searching for MCP servers matching 'test'" in result.output
    assert "Test Server" in result.output
    assert "A test server" in result.output
    assert "Found 1 server(s) matching search criteria" in result.output
    mock_repo_manager.search_servers.assert_called_once_with("test")
