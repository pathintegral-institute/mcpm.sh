import os
import sys
from pathlib import Path
from typing import Optional, TextIO


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


DEFAULT_ROOT_STDERR_LOG_DIR = get_log_directory("mcpm") / "errlogs"


class ServerLogManager:
    """
    A manager for server error logs.
    """

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_log_dir = root_dir if root_dir else DEFAULT_ROOT_STDERR_LOG_DIR
        os.makedirs(self.root_log_dir, exist_ok=True)
        self._log_files: dict[str, TextIO] = {}

    def open_errlog_file(self, server_id: str) -> TextIO:
        if server_id not in self._log_files or self._log_files[server_id].closed:
            log_file = self.root_log_dir / f"{server_id}.log"
            # use line buffering, flush to disk when meeting a newline
            self._log_files[server_id] = log_file.open("a", encoding="utf-8", buffering=1)
        return self._log_files[server_id]

    def close_errlog_file(self, server_id: str) -> None:
        if server_id in self._log_files and not self._log_files[server_id].closed:
            self._log_files[server_id].flush()
            self._log_files[server_id].close()
            del self._log_files[server_id]

    def close_all(self) -> None:
        for server_id in list(self._log_files.keys()):
            self.close_errlog_file(server_id)
