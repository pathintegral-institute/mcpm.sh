"""
Platform-specific utilities for MCPM router.
This module provides functions to handle platform-specific operations,
such as determining appropriate log directories based on the operating system.
"""

import os
import sys
from pathlib import Path


def get_log_directory(app_name: str = "mcpm") -> Path:
    """
    Return the appropriate log directory path based on the current operating system.

    Args:
        app_name: The name of the application, used in the path

    Returns:
        Path object representing the log directory
    """
    # macOS
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Logs" / app_name / "logs"

    # Windows
    elif sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            return Path(localappdata) / app_name / "logs"
        return Path.home() / "AppData" / "Local" / app_name / "logs"

    # Linux and other Unix-like systems
    else:
        # Check if XDG_DATA_HOME is defined
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            return Path(xdg_data_home) / app_name / "logs"

        # Default to ~/.local/share if XDG_DATA_HOME is not defined
        return Path.home() / ".local" / "share" / app_name / "logs"


def get_pid_directory(app_name: str = "mcpm") -> Path:
    """
    Return the appropriate PID directory path based on the current operating system.

    Args:
        app_name: The name of the application, used in the path

    Returns:
        Path object representing the PID directory
    """
    # macOS
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name

    # Windows
    elif sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            return Path(localappdata) / app_name
        return Path.home() / "AppData" / "Local" / app_name

    # Linux and other Unix-like systems
    else:
        # Attempt to respect XDG_DATA_HOME but fall back to /tmp when the
        # configured location is not writable (e.g. in restricted test
        # environments).
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        candidate = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"

        # If the chosen directory is not writable fall back to a location under
        # */tmp* which is always available during testing.
        try:
            test_path = candidate / app_name
            test_path.mkdir(parents=True, exist_ok=True)
            return test_path
        except PermissionError:
            return Path("/tmp") / app_name


def get_frpc_directory(app_name: str = "mcpm") -> Path:
    """
    Return the appropriate FRPC directory path based on the current operating system.

    Args:
        app_name: The name of the application, used in the path

    Returns:
        Path object representing the FRPC directory
    """
    # macOS
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name / "frpc"

    # Windows
    elif sys.platform == "win32":
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            return Path(localappdata) / app_name / "frpc"
        return Path.home() / "AppData" / "Local" / app_name / "frpc"

    # Linux and other Unix-like systems
    else:
        # Check if XDG_DATA_HOME is defined
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            return Path(xdg_data_home) / app_name / "frpc"

        # Default to ~/.local/share if XDG_DATA_HOME is not defined
        return Path.home() / ".local" / "share" / app_name / "frpc"


NPX_CMD = "npx" if sys.platform != "win32" else "npx.cmd"
