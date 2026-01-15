"""
Platform-specific utilities for MCPM router.
This module provides functions to handle platform-specific operations,
such as determining appropriate log directories based on the operating system.
"""

import os
import sys
from pathlib import Path


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
        # Check if XDG_DATA_HOME is defined
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            return Path(xdg_data_home) / app_name

        # Default to ~/.local/share if XDG_DATA_HOME is not defined
        return Path.home() / ".local" / "share" / app_name


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


def get_config_directory(app_name: str = "mcpm") -> Path:
    """
    Return the configuration directory path.

    Uses ~/.config/mcpm on all platforms for consistency.
    Path is returned as a Path object with correct separators for the current OS.

    Note: This intentionally differs from get_pid_directory() and get_frpc_directory()
    which use platform-specific paths. The config directory uses a unified location
    to simplify user configuration and documentation across all platforms.

    Args:
        app_name: The name of the application, used in the path

    Returns:
        Path object representing the configuration directory
    """
    return Path.home() / ".config" / app_name


def get_data_directory(app_name: str = "mcpm") -> Path:
    """
    Return the data directory path.

    Uses ~/.mcpm on all platforms for consistency (stores server metadata, etc.).
    Path is returned as a Path object with correct separators for the current OS.

    Note: This intentionally differs from get_pid_directory() and get_frpc_directory()
    which use platform-specific paths. The data directory uses a unified location
    to simplify user configuration and documentation across all platforms.

    Args:
        app_name: The name of the application, used in the path

    Returns:
        Path object representing the data directory
    """
    return Path.home() / f".{app_name}"


NPX_CMD = "npx" if sys.platform != "win32" else "npx.cmd"
