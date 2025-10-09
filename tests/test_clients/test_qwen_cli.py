"""
Test for Qwen CLI manager
"""

import os
import tempfile
from unittest.mock import patch

from mcpm.clients.managers.qwen_cli import QwenCliManager


def test_qwen_cli_manager_initialization():
    """Test QwenCliManager initialization"""
    # Test with default config path
    manager = QwenCliManager()
    assert manager.client_key == "qwen-cli"
    assert manager.display_name == "Qwen CLI"
    assert manager.download_url == "https://github.com/QwenLM/qwen-code"
    assert manager.config_path == os.path.expanduser("~/.qwen/settings.json")

    # Test with custom config path
    custom_path = "/tmp/custom_settings.json"
    manager = QwenCliManager(config_path_override=custom_path)
    assert manager.config_path == custom_path


def test_qwen_cli_manager_get_empty_config():
    """Test QwenCliManager _get_empty_config method"""
    manager = QwenCliManager()
    config = manager._get_empty_config()
    assert "mcpServers" in config
    assert "theme" in config
    assert "selectedAuthType" in config
    assert config["mcpServers"] == {}


def test_qwen_cli_manager_is_client_installed():
    """Test QwenCliManager is_client_installed method"""
    manager = QwenCliManager()
    
    # Mock shutil.which to return a path (simulating installed client)
    with patch("shutil.which", return_value="/usr/local/bin/qwen") as mock_which:
        assert manager.is_client_installed() is True
        mock_which.assert_called_with("qwen")
    
    # Mock shutil.which to return None (simulating uninstalled client)
    with patch("shutil.which", return_value=None) as mock_which:
        assert manager.is_client_installed() is False
        mock_which.assert_called_with("qwen")


def test_qwen_cli_manager_is_client_installed_windows():
    """Test QwenCliManager is_client_installed method on Windows"""
    manager = QwenCliManager()
    
    with patch.object(manager, "_system", "Windows"):
        # Mock shutil.which to return a path (simulating installed client)
        with patch("shutil.which", return_value="C:\\Program Files\\qwen\\qwen.exe") as mock_which:
            assert manager.is_client_installed() is True
            mock_which.assert_called_with("qwen.exe")
        
        # Mock shutil.which to return None (simulating uninstalled client)
        with patch("shutil.which", return_value=None) as mock_which:
            assert manager.is_client_installed() is False
            mock_which.assert_called_with("qwen.exe")


def test_qwen_cli_manager_get_empty_config_structure():
    """Test QwenCliManager _get_empty_config method returns expected structure"""
    manager = QwenCliManager()
    config = manager._get_empty_config()
    
    # Check that required keys are present
    assert "mcpServers" in config
    assert "theme" in config
    assert "selectedAuthType" in config
    
    # Check default values
    assert config["mcpServers"] == {}
    assert config["theme"] == "Qwen Dark"
    assert config["selectedAuthType"] == "openai"


def test_qwen_cli_manager_get_client_info():
    """Test QwenCliManager get_client_info method"""
    manager = QwenCliManager()
    info = manager.get_client_info()
    assert info["name"] == "Qwen CLI"
    assert info["download_url"] == "https://github.com/QwenLM/qwen-code"
    assert info["config_file"] == os.path.expanduser("~/.qwen/settings.json")
    assert info["description"] == "Alibaba's Qwen CLI tool"