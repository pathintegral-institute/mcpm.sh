"""
FastMCP middleware adapters for MCPM monitoring and authentication.
"""

import time

from fastmcp.server.middleware import Middleware

from mcpm.monitor.base import AccessEventType, AccessMonitor


class MCPMMonitoringMiddleware(Middleware):
    """FastMCP middleware that integrates with MCPM's AccessMonitor system."""

    def __init__(self, access_monitor: AccessMonitor):
        self.monitor = access_monitor

    async def on_call_tool(self, context, call_next):
        """Track tool invocation events."""
        start_time = time.time()
        tool_name = getattr(context, "tool_name", "unknown")
        server_id = getattr(context, "server_id", "unknown")

        try:
            result = await call_next(context)
            await self.monitor.track_event(
                event_type=AccessEventType.TOOL_INVOCATION,
                server_id=server_id,
                resource_id=tool_name,
                duration_ms=int((time.time() - start_time) * 1000),
                success=True,
                metadata={"middleware": "fastmcp"},
            )
            return result
        except Exception as e:
            await self.monitor.track_event(
                event_type=AccessEventType.TOOL_INVOCATION,
                server_id=server_id,
                resource_id=tool_name,
                duration_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=str(e),
                metadata={"middleware": "fastmcp"},
            )
            raise

    async def on_read_resource(self, context, call_next):
        """Track resource access events."""
        start_time = time.time()
        resource_uri = getattr(context, "resource_uri", "unknown")
        server_id = getattr(context, "server_id", "unknown")

        try:
            result = await call_next(context)
            await self.monitor.track_event(
                event_type=AccessEventType.RESOURCE_ACCESS,
                server_id=server_id,
                resource_id=resource_uri,
                duration_ms=int((time.time() - start_time) * 1000),
                success=True,
                metadata={"middleware": "fastmcp"},
            )
            return result
        except Exception as e:
            await self.monitor.track_event(
                event_type=AccessEventType.RESOURCE_ACCESS,
                server_id=server_id,
                resource_id=resource_uri,
                duration_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=str(e),
                metadata={"middleware": "fastmcp"},
            )
            raise

    async def on_get_prompt(self, context, call_next):
        """Track prompt execution events."""
        start_time = time.time()
        prompt_name = getattr(context, "prompt_name", "unknown")
        server_id = getattr(context, "server_id", "unknown")

        try:
            result = await call_next(context)
            await self.monitor.track_event(
                event_type=AccessEventType.PROMPT_EXECUTION,
                server_id=server_id,
                resource_id=prompt_name,
                duration_ms=int((time.time() - start_time) * 1000),
                success=True,
                metadata={"middleware": "fastmcp"},
            )
            return result
        except Exception as e:
            await self.monitor.track_event(
                event_type=AccessEventType.PROMPT_EXECUTION,
                server_id=server_id,
                resource_id=prompt_name,
                duration_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=str(e),
                metadata={"middleware": "fastmcp"},
            )
            raise


class MCPMAuthMiddleware(Middleware):
    """FastMCP middleware that integrates with MCPM's authentication system."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def on_request(self, context, call_next):
        """Authenticate requests using MCPM's auth configuration."""
        try:
            # Multiple approaches to get headers
            headers = None
            auth_header = None

            # Method 1: Try FastMCP's built-in helper
            try:
                from fastmcp.server.dependencies import get_http_headers

                headers = get_http_headers()
                auth_header = headers.get("authorization") or headers.get("Authorization")
            except (RuntimeError, ImportError):
                pass

            # Method 2: Try accessing from context
            if not auth_header and hasattr(context, "request"):
                request = context.request
                if hasattr(request, "headers"):
                    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")

            # Method 3: Try direct context headers
            if not auth_header and hasattr(context, "headers"):
                headers = context.headers
                auth_header = headers.get("Authorization") or headers.get("authorization")

            # Method 4: Check for auth in context metadata
            if not auth_header and hasattr(context, "metadata"):
                metadata = context.metadata
                auth_header = metadata.get("authorization") or metadata.get("Authorization")

            if not auth_header:
                # For debugging: print available context attributes
                # print(f"DEBUG: Context type: {type(context)}, attrs: {dir(context)}")
                raise ValueError("Authorization header required")

            # Extract API key from Bearer token or direct key
            api_key = None
            if auth_header.startswith("Bearer "):
                api_key = auth_header[7:]
            elif auth_header.startswith("bearer "):
                api_key = auth_header[7:]
            else:
                api_key = auth_header

            if api_key != self.api_key:
                raise ValueError("Invalid API key")

        except ValueError:
            # Re-raise authentication errors
            raise
        except Exception:
            # For any other error, skip auth (might be stdio mode)
            pass

        return await call_next(context)


class MCPMUsageTrackingMiddleware(Middleware):
    """FastMCP middleware that integrates with MCPM's usage tracking system."""

    def __init__(self):
        pass

    async def on_request(self, context, call_next):
        """Track usage for servers and operations."""
        try:
            # Import here to avoid circular imports
            from mcpm.commands.usage import record_server_usage

            server_id = getattr(context, "server_id", None)
            if server_id:
                record_server_usage(server_id, action="proxy")
        except ImportError:
            # Usage tracking not available
            pass

        return await call_next(context)
