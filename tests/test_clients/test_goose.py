import os
import tempfile
from unittest.mock import patch

import pytest
from ruamel.yaml import YAML

from mcpm.clients.managers.goose import GooseClientManager


@pytest.fixture
def temp_yml_config():
    with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml") as f:
        # Built in extention
        config = {
            "computercontroller": {
                "bundled": True,
                "display_name": "Computer Controller",
                "enabled": False,
                "name": "computercontroller",
                "timeout": 300,
                "type": "builtin",
            }
        }
        YAML().dump({"extensions": config}, f)
        temp_path = f.name

    yield temp_path
    # Clean up
    os.unlink(temp_path)


@pytest.fixture
def goose_manager(temp_yml_config):
    return GooseClientManager(config_path=temp_yml_config)


def test_list_servers(goose_manager):
    servers = goose_manager.list_servers()
    assert "computercontroller" in servers


def test_get_server(goose_manager):
    server = goose_manager.get_server("computercontroller")
    assert server is not None
    assert server.name == "computercontroller"


def test_server_operation(goose_manager):
    # builtin extension
    success = goose_manager.add_server({"name": "test-server", "type": "builtin", "enabled": True}, "test-server")
    assert success

    server = goose_manager.get_server("test-server")
    assert server is not None
    assert server.name == "test-server"

    # stdio extension
    success = goose_manager.add_server(
        {
            "name": "stdio-server",
            "type": "stdio",
            "enabled": True,
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-test"],
        },
        "stdio-server",
    )
    assert success

    server = goose_manager.get_server("stdio-server")
    assert server is not None
    assert server.name == "stdio-server"

    # remove server
    success = goose_manager.remove_server("test-server")
    assert success

    assert goose_manager.get_server("test-server") is None


def test_is_client_installed(goose_manager):
    with patch("os.path.isdir", return_value=True):
        assert goose_manager.is_client_installed()

    with patch("os.path.isdir", return_value=False):
        assert not goose_manager.is_client_installed()
