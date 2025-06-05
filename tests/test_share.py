"""
Tests for the share command in MCPM
"""

import sys
from unittest.mock import Mock, patch

from click.testing import CliRunner

from src.mcpm.commands.share import (
    find_mcp_proxy,
    monitor_for_errors,
    share,
    terminate_process,
)


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

    def test_share_command_no_mcp_proxy(self, monkeypatch):
        """Test share command when mcp-proxy is not installed"""
        # Mock find_mcp_proxy to return None
        monkeypatch.setattr("src.mcpm.commands.share.find_mcp_proxy", lambda: None)

        # Run the command
        runner = CliRunner()
        with patch.object(sys, "exit") as mock_exit:
            result = runner.invoke(share, ["test command"])

            # Verify the command failed with the right error
            assert mock_exit.called
            assert "mcp-proxy not found" in result.output
