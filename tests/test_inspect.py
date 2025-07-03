"""
Tests for MCPM v2.0 inspect command (global configuration model)
"""

from unittest.mock import patch

from click.testing import CliRunner

from mcpm.commands.inspect import inspect
from mcpm.core.schema import STDIOServerConfig
from mcpm.global_config import GlobalConfigManager


def test_inspect_server_success(tmp_path):
    """Test successful server inspection from global configuration"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    # Add a test server to global config
    test_server = STDIOServerConfig(
        name="test-server", command="echo", args=["hello", "world"], env={"TEST_VAR": "test-value"}
    )
    global_config_manager.add_server(test_server)

    # Mock the global config manager and subprocess
    with (
        patch("mcpm.commands.inspect.global_config_manager", global_config_manager),
        patch("mcpm.commands.inspect.subprocess.call") as mock_call,
    ):
        mock_call.return_value = 0

        runner = CliRunner()
        result = runner.invoke(inspect, ["test-server"])

        assert result.exit_code == 0
        assert "MCPM Inspector" in result.output
        assert "Inspecting server: test-server" in result.output
        assert "Found server in: global configuration" in result.output
        assert "Server will be launched via: mcpm run test-server" in result.output

        # Verify subprocess.call was called with the correct inspector command
        mock_call.assert_called_once()
        call_args = mock_call.call_args[0][0]

        # The command should be: ["npx", "@modelcontextprotocol/inspector", "mcpm", "run", "test-server"]
        assert "npx" in call_args[0]
        assert "@modelcontextprotocol/inspector" in call_args[1]
        assert "mcpm" in call_args[2]
        assert "run" in call_args[3]
        assert "test-server" in call_args[4]


def test_inspect_server_not_found(tmp_path):
    """Test inspecting non-existent server from global configuration"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    # Mock the global config manager
    with patch("mcpm.commands.inspect.global_config_manager", global_config_manager):
        runner = CliRunner()
        result = runner.invoke(inspect, ["non-existent-server"])

        assert result.exit_code == 1
        assert "Server 'non-existent-server' not found" in result.output
        assert "mcpm ls" in result.output
        assert "mcpm install" in result.output


def test_inspect_direct_execution(tmp_path):
    """Test inspection runs directly without confirmation"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    # Add a test server to global config
    test_server = STDIOServerConfig(name="direct-server", command="node", args=["server.js"])
    global_config_manager.add_server(test_server)

    # Mock the global config manager and subprocess
    with (
        patch("mcpm.commands.inspect.global_config_manager", global_config_manager),
        patch("mcpm.commands.inspect.subprocess.call") as mock_call,
    ):
        mock_call.return_value = 0

        runner = CliRunner()
        result = runner.invoke(inspect, ["direct-server"])

        assert result.exit_code == 0
        assert "Starting Inspector for server 'direct-server'" in result.output
        assert "Inspector UI will open in your web browser" in result.output
        mock_call.assert_called_once()


def test_inspect_empty_server_name():
    """Test inspecting with empty server name"""
    runner = CliRunner()
    result = runner.invoke(inspect, [""])

    assert result.exit_code == 1
    assert "Server name cannot be empty" in result.output


def test_inspect_whitespace_server_name():
    """Test inspecting with whitespace-only server name"""
    runner = CliRunner()
    result = runner.invoke(inspect, ["   "])

    assert result.exit_code == 1
    assert "Server name cannot be empty" in result.output


def test_inspect_keyboard_interrupt(tmp_path):
    """Test inspection interrupted by keyboard"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    # Add a test server to global config
    test_server = STDIOServerConfig(name="interrupt-server", command="sleep", args=["10"])
    global_config_manager.add_server(test_server)

    # Mock the global config manager and subprocess
    with (
        patch("mcpm.commands.inspect.global_config_manager", global_config_manager),
        patch("mcpm.commands.inspect.subprocess.call") as mock_call,
    ):
        mock_call.side_effect = KeyboardInterrupt()

        runner = CliRunner()
        result = runner.invoke(inspect, ["interrupt-server"])

        assert result.exit_code == 130
        assert "Inspector process terminated by keyboard interrupt" in result.output


def test_inspect_file_not_found(tmp_path):
    """Test inspection with missing npx command"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    # Add a test server to global config
    test_server = STDIOServerConfig(name="missing-npx-server", command="echo", args=["test"])
    global_config_manager.add_server(test_server)

    # Mock the global config manager and subprocess
    with (
        patch("mcpm.commands.inspect.global_config_manager", global_config_manager),
        patch("mcpm.commands.inspect.subprocess.call") as mock_call,
    ):
        mock_call.side_effect = FileNotFoundError()

        runner = CliRunner()
        result = runner.invoke(inspect, ["missing-npx-server"])

        assert result.exit_code == 1
        assert "Could not find npx" in result.output
        assert "Please make sure Node.js is installed" in result.output


def test_inspect_permission_error(tmp_path):
    """Test inspection with permission error"""
    # Setup temporary global config
    global_config_path = tmp_path / "servers.json"
    global_config_manager = GlobalConfigManager(config_path=str(global_config_path))

    # Add a test server to global config
    test_server = STDIOServerConfig(name="permission-server", command="echo", args=["test"])
    global_config_manager.add_server(test_server)

    # Mock the global config manager and subprocess
    with (
        patch("mcpm.commands.inspect.global_config_manager", global_config_manager),
        patch("mcpm.commands.inspect.subprocess.call") as mock_call,
    ):
        mock_call.side_effect = PermissionError()

        runner = CliRunner()
        result = runner.invoke(inspect, ["permission-server"])

        assert result.exit_code == 1
        assert "Permission denied" in result.output
