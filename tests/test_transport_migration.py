"""
Tests for SSE to Streamable HTTP transport migration
"""

from unittest.mock import MagicMock, patch

import pytest

from mcpm.migration.transport_migrator import TransportMigrator


@pytest.fixture
def mock_registry():
    with patch("mcpm.migration.transport_migrator.ClientRegistry") as MockRegistry:
        registry = MockRegistry.return_value
        yield registry


def test_transport_migration_initialization(mock_registry):
    """Test that the migrator initializes correctly"""
    migrator = TransportMigrator()
    assert migrator.registry is not None


def test_migrate_all_clients_no_updates(mock_registry):
    """Test migration when no updates are needed"""
    # Setup mock manager
    mock_manager = MagicMock()
    mock_manager.is_client_installed.return_value = True
    # Explicitly set the attribute so getattr doesn't return a Mock
    mock_manager.configure_key_name = "mcpServers"

    mock_manager._load_config.return_value = {"mcpServers": {"test-server": {"transport": "stdio", "command": "test"}}}

    mock_registry.get_all_client_managers.return_value = {"test-client": mock_manager}

    migrator = TransportMigrator()
    changes_made = migrator.migrate_all_clients()

    assert not changes_made
    mock_manager._save_config.assert_not_called()


def test_migrate_all_clients_with_sse_update(mock_registry):
    """Test migration when SSE transport needs updating"""
    # Setup mock manager
    mock_manager = MagicMock()
    mock_manager.display_name = "Test Client"
    mock_manager.is_client_installed.return_value = True
    # Explicitly set the attribute so getattr doesn't return a Mock
    mock_manager.configure_key_name = "mcpServers"

    config = {
        "mcpServers": {
            "sse-server": {"transport": "sse", "url": "http://localhost:3000/sse"},
            "legacy-server": {"url": "http://localhost:8080/sse/v1"},
        }
    }
    mock_manager._load_config.return_value = config

    mock_registry.get_all_client_managers.return_value = {"test-client": mock_manager}

    migrator = TransportMigrator()
    changes_made = migrator.migrate_all_clients()

    assert changes_made

    # Verify save was called
    mock_manager._save_config.assert_called_once()
    saved_config = mock_manager._save_config.call_args[0][0]

    # Verify updates
    assert saved_config["mcpServers"]["sse-server"]["transport"] == "streamable-http"
    assert saved_config["mcpServers"]["sse-server"]["url"] == "http://localhost:3000/mcp"
    assert saved_config["mcpServers"]["legacy-server"]["url"] == "http://localhost:8080/mcp/v1"


def test_migrate_vscode_structure(mock_registry):
    """Test migration for VSCode nested structure"""
    mock_manager = MagicMock()
    mock_manager.display_name = "VSCode"
    mock_manager.is_client_installed.return_value = True

    config = {"mcp": {"servers": {"sse-server": {"transport": "sse", "url": "http://localhost:3000/sse"}}}}
    mock_manager._load_config.return_value = config

    mock_registry.get_all_client_managers.return_value = {"vscode": mock_manager}

    migrator = TransportMigrator()
    changes_made = migrator.migrate_all_clients()

    assert changes_made

    saved_config = mock_manager._save_config.call_args[0][0]
    assert saved_config["mcp"]["servers"]["sse-server"]["transport"] == "streamable-http"
    assert saved_config["mcp"]["servers"]["sse-server"]["url"] == "http://localhost:3000/mcp"
