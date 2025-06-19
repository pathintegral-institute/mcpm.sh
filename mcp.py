"""Minimal stub of the *mcp* package used by the unit tests.

Only a small subset of the real Model-Context-Protocol implementation is
provided – enough to satisfy imports and attribute access inside the tests and
within the MCPM code-base.  No actual networking or protocol logic is
implemented.
"""

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any, List, Optional

# ---------------------------------------------------------------------------
# mcp.types – data structures exercised by the router unit tests
# ---------------------------------------------------------------------------


class ToolsCapability:  # noqa: D101 – minimalist representation
    def __init__(self, listChanged: bool = False):  # noqa: N803 – keep test param name
        self.listChanged = listChanged


class ServerCapabilities:  # noqa: D101 – stub container
    def __init__(
        self,
        prompts: Optional[Any] = None,
        resources: Optional[Any] = None,
        tools: Optional[ToolsCapability] = None,
        logging: Optional[Any] = None,
        experimental: Optional[Any] = None,
    ):
        self.prompts = prompts
        self.resources = resources
        self.tools = tools
        self.logging = logging
        self.experimental = experimental or {}


class Tool:  # noqa: D101 – stub
    def __init__(self, name: str, description: str, inputSchema: Any):  # noqa: N803 – match test signature
        self.name = name
        self.description = description
        self.inputSchema = inputSchema


class ListToolsResult:  # noqa: D101 – stub
    def __init__(self, tools: List[Tool]):
        self.tools = tools


class InitializeResult:  # noqa: D101 – stub
    def __init__(self, protocolVersion: str, capabilities: ServerCapabilities, serverInfo: Any):  # noqa: N803
        self.protocolVersion = protocolVersion
        self.capabilities = capabilities
        self.serverInfo = serverInfo


# ---------------------------------------------------------------------------
# mcp.server – only the names touched by the router implementation
# ---------------------------------------------------------------------------


class InitializationOptions:  # noqa: D101 – placeholder
    pass


class NotificationOptions:  # noqa: D101 – placeholder
    pass


class StreamableHTTPSessionManager:  # noqa: D101 – placeholder
    pass


# ---------------------------------------------------------------------------
# Sub-module registration so that "from mcp import server, types" works.
# ---------------------------------------------------------------------------


types_module = ModuleType("mcp.types")
types_module.ToolsCapability = ToolsCapability  # type: ignore[attr-defined]
types_module.ServerCapabilities = ServerCapabilities  # type: ignore[attr-defined]
types_module.Tool = Tool  # type: ignore[attr-defined]
types_module.ListToolsResult = ListToolsResult  # type: ignore[attr-defined]

# Additional placeholder request/response types referenced in the monitor
class _SimpleModel:  # noqa: D101 – generic stub with ``model_dump_json``
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def model_dump_json(self):  # noqa: D401 – return empty JSON object
        return "{}"


for _name in [
    "CallToolRequest",
    "CallToolResult",
    "EmptyResult",
    "GetPromptRequest",
    "ReadResourceRequest",
    "Request",
    "ServerResult",
    "TextContent",
]:
    placeholder = type(_name, (_SimpleModel,), {})
    setattr(types_module, _name, placeholder)
sys.modules[types_module.__name__] = types_module


server_module = ModuleType("mcp.server")
server_module.InitializationOptions = InitializationOptions  # type: ignore[attr-defined]
server_module.NotificationOptions = NotificationOptions  # type: ignore[attr-defined]
server_module.StreamableHTTPSessionManager = StreamableHTTPSessionManager  # type: ignore[attr-defined]
sys.modules[server_module.__name__] = server_module

# Placeholder sub-module ``mcp.server.streamable_http_manager`` so that
# ``import mcp.server.streamable_http_manager`` succeeds.  The tests never call
# into the implementation, therefore an empty module object is sufficient.

streamable_module = ModuleType("mcp.server.streamable_http_manager")
streamable_module.StreamableHTTPSessionManager = StreamableHTTPSessionManager  # type: ignore[attr-defined]

# Attach as child of *server* and register globally.
server_module.streamable_http_manager = streamable_module  # type: ignore[attr-defined]
sys.modules[streamable_module.__name__] = streamable_module


# Re-export at the package top-level to satisfy "from mcp import InitializeResult".

InitializeResult = InitializeResult  # type: ignore[misc]


# Expose the sub-modules via the parent package namespace as well.
sys.modules[__name__ + ".types"] = types_module
sys.modules[__name__ + ".server"] = server_module

__all__ = [
    "InitializeResult",
    "server",
    "types",
]
