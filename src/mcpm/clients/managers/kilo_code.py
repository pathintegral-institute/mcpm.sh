"""Kilo Code client integration for MCPM.

This manager follows the simple *JSON* configuration style that the majority
of other client managers use in the project.  The exact on-disk format for
Kilo Code is currently undocumented; therefore we adopt the same minimal
structure as with the other managers so that users can still benefit from the
core MCPM workflow (adding and removing servers, activating profiles, …).

If the real client stores its configuration in a different location or uses a
different file format the implementation can be updated later without
impacting the rest of the code-base.
"""

from __future__ import annotations

import logging
import os
import shutil
from typing import Any, Dict

from mcpm.clients.base import JSONClientManager

logger = logging.getLogger(__name__)


class KiloCodeManager(JSONClientManager):
    """Manage Kilo Code MCP server configurations."""

    # ---------------------------------------------------------------------
    # Static client metadata – visible to callers via ``get_client_info``.
    # ---------------------------------------------------------------------
    client_key = "kilo-code"
    display_name = "Kilo Code"
    download_url = "https://kilocode.ai/"

    def __init__(self, config_path: str | None = None):
        super().__init__()

        # Heuristic configuration file locations that mirror the conventions
        # used by other managers in the project.
        if config_path is not None:
            self.config_path = config_path
        else:
            if self._system == "Windows":
                self.config_path = os.path.join(
                    os.environ.get("APPDATA", ""),
                    "KiloCode",
                    "mcp_config.json",
                )
            else:  # macOS & Linux
                self.config_path = os.path.expanduser("~/.kilocode/mcp_config.json")

    # ------------------------------------------------------------------
    # Optional helper for the stubbed configuration file – provides the
    # root *mcpServers* mapping so that the code does not crash on first use.
    # ------------------------------------------------------------------
    def _get_empty_config(self) -> Dict[str, Any]:  # noqa: D401 – override
        return {"mcpServers": {}}

    # ------------------------------------------------------------------
    # Simple installation check – reuse the approach of the Claude Code
    # manager by looking for the *kilocode* executable on the ``PATH``.
    # ------------------------------------------------------------------
    def is_client_installed(self) -> bool:  # noqa: D401 – heuristic check
        executable = "kilocode.exe" if self._system == "Windows" else "kilocode"
        return shutil.which(executable) is not None

    # ------------------------------------------------------------------
    # Provide a slightly richer info dict containing a short description so
    # that the CLI can display something meaningful.
    # ------------------------------------------------------------------
    def get_client_info(self) -> Dict[str, str]:  # noqa: D401 – override
        info = super().get_client_info()
        info["description"] = "Kilo Code AI coding assistant"
        return info

