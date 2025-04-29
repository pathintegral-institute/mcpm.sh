import os
from pathlib import Path
from typing import Optional, TextIO

from .platform import get_log_directory

DEFAULT_ROOT_STDERR_LOG_DIR = get_log_directory("mcpm") / "errlogs"

class ServerErrorLogManager:
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
        for server_id in self._log_files:
            self.close_errlog_file(server_id)
