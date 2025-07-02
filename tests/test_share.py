"""
Tests for MCPM v2.0 share command (global configuration model)
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from mcpm.commands.share import (
    find_mcp_proxy,
    monitor_for_errors,
    share,
    terminate_process,
    find_installed_server,
    build_server_command,
)
from mcpm.core.schema import STDIOServerConfig
from mcpm.global_config import GlobalConfigManager


class TestShareCommand:
    """Tests for the share command"""

    def test_find_mcp_proxy_found(self, monkeypatch):
        """Test finding mcp-proxy when it exists in PATH"""
        # Mock shutil.which to return a path
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/mcp-proxy")

        assert find_mcp_proxy() == "/usr/bin/mcp-proxy"

    def test_find_mcp_proxy_not_found(self, monkeypatch):
        """Test finding mcp-proxy when it does not exist in PATH"""
        # Mock shutil.which to return None
        monkeypatch.setattr("shutil.which", lambda _: None)

        assert find_mcp_proxy() is None

    def test_monitor_for_errors_with_known_error(self):
        """Test error detection with a known error pattern"""
        error_line = "Error: RuntimeError: Received request before initialization was complete"

        result = monitor_for_errors(error_line)

        assert result is not None
        assert "Protocol initialization error" in result

    def test_monitor_for_errors_connection_error(self):
        """Test error detection with connection broken error"""
        error_line = "Exception: anyio.BrokenResourceError occurred during processing"

        result = monitor_for_errors(error_line)

        assert result is not None
        assert "Connection broken unexpectedly" in result

    def test_monitor_for_errors_taskgroup_error(self):
        """Test error detection with task group error"""
        error_line = "Error: ExceptionGroup: unhandled errors in a TaskGroup"

        result = monitor_for_errors(error_line)

        assert result is not None
        assert "Server task error detected" in result

    def test_monitor_for_errors_no_error(self):
        """Test error detection with no error patterns"""
        normal_line = "Server started successfully on port 8000"

        result = monitor_for_errors(normal_line)

        assert result is None

    def test_terminate_process_already_terminated(self):
        """Test terminating a process that's already terminated"""
        mock_process = Mock()
        mock_process.poll.return_value = 0  # Process already exited

        result = terminate_process(mock_process)

        assert result is True
        mock_process.terminate.assert_not_called()

    def test_terminate_process_successful_termination(self):
        """Test successful termination of a process"""
        mock_process = Mock()
        # Process is running, then terminates after SIGTERM
        mock_process.poll.side_effect = [None, 0]

        result = terminate_process(mock_process, timeout=1)

        assert result is True
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_not_called()

    @patch("time.sleep")  # Add sleep patch to avoid actual sleep
    def test_terminate_process_needs_sigkill(self, mock_sleep):
        """Test termination of a process that needs SIGKILL"""
        mock_process = Mock()
        # First 20 poll calls return None (not terminated)
        # Then the 21st call returns 0 (terminated after SIGKILL)
        mock_process.poll.side_effect = [None] * 20 + [0]

        result = terminate_process(mock_process, timeout=1)

        assert result is True
        mock_process.terminate.assert_called_once()
        mock_process.kill.assert_called_once()

    def test_find_installed_server(self):
        """Test finding server in global configuration"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup temporary global config
            global_config_path = Path(tmp_dir) / "servers.json"
            global_config_manager = GlobalConfigManager(config_path=str(global_config_path))
            
            # Add a test server to global config
            test_server = STDIOServerConfig(
                name="test-server",
                command="echo",
                args=["hello"]
            )
            global_config_manager.add_server(test_server)
            
            # Mock the global config manager
            with patch("mcpm.commands.share.global_config_manager", global_config_manager):
                server_config, location = find_installed_server("test-server")
                
                assert server_config is not None
                assert server_config.name == "test-server"
                assert location == "global"
                
                # Test non-existent server
                server_config, location = find_installed_server("non-existent")
                assert server_config is None
                assert location is None

    def test_build_server_command(self):
        """Test building server command"""
        test_server = STDIOServerConfig(
            name="test-server",
            command="echo",
            args=["hello"]
        )
        
        command = build_server_command(test_server, "test-server")
        assert command == "mcpm run test-server"
        
        # Test with None server config
        command = build_server_command(None, "test-server")
        assert command is None

    def test_share_server_not_found(self):
        """Test sharing non-existent server"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup temporary global config
            global_config_path = Path(tmp_dir) / "servers.json"
            global_config_manager = GlobalConfigManager(config_path=str(global_config_path))
            
            # Mock the global config manager
            with patch("mcpm.commands.share.global_config_manager", global_config_manager):
                runner = CliRunner()
                result = runner.invoke(share, ["non-existent-server"])
                
                assert result.exit_code == 1
                assert "Server 'non-existent-server' not found" in result.output
                assert "mcpm ls" in result.output
                assert "mcpm install" in result.output

    def test_share_empty_server_name(self):
        """Test sharing with empty server name"""
        runner = CliRunner()
        result = runner.invoke(share, [""])
        
        assert result.exit_code == 1
        assert "Server name cannot be empty" in result.output

    def test_share_command_no_mcp_proxy(self):
        """Test share command when mcp-proxy is not installed"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Setup temporary global config
            global_config_path = Path(tmp_dir) / "servers.json"
            global_config_manager = GlobalConfigManager(config_path=str(global_config_path))
            
            # Add a test server to global config
            test_server = STDIOServerConfig(
                name="test-server",
                command="echo",
                args=["hello"]
            )
            global_config_manager.add_server(test_server)
            
            # Mock the global config manager and make mcp-proxy not found
            with patch("mcpm.commands.share.global_config_manager", global_config_manager), \
                 patch("mcpm.commands.share.find_mcp_proxy", return_value=None):
                
                runner = CliRunner()
                result = runner.invoke(share, ["test-server"])
                
                assert result.exit_code == 1
                assert "mcp-proxy not found in PATH" in result.output
                assert "install mcp-proxy" in result.output

    def test_share_help_shows_v2_usage(self):
        """Test that share help shows v2.0 server name usage"""
        runner = CliRunner()
        result = runner.invoke(share, ["--help"])
        
        assert result.exit_code == 0
        assert "SERVER_NAME" in result.output
        assert "mcpm share time" in result.output
        assert "installed server" in result.output
        assert "global configuration" in result.output
