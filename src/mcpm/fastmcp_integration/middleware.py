"""
FastMCP middleware adapters for MCPM monitoring and authentication.
"""

import logging
import time
import uuid
from typing import Any

import mcp.types as mt
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext

from mcpm.monitor.base import AccessEventType, AccessMonitor, SessionSource, SessionTransport

# MCPMMonitoringMiddleware removed - functionality moved to MCPMUnifiedTrackingMiddleware


class MCPMDebugMiddleware(Middleware):
    """Debug middleware that logs all proxy activity including notifications when debug is enabled.

    Note: This middleware intercepts messages flowing FROM clients TO servers through the proxy.
    Progress notifications that flow FROM servers TO clients are handled differently and will
    not appear in the middleware logs. To debug progress notifications, check the FastMCP
    proxy logs and the Context.report_progress debug messages.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def on_message(
        self,
        context: MiddlewareContext[Any],
        call_next: CallNext[Any, Any],
    ) -> Any:
        """Log all messages (requests and notifications) with basic information."""
        message_type = context.type
        method = context.method or "unknown"
        source = context.source

        self.logger.debug(f"[PROXY DEBUG] {message_type.upper()} - {method} from {source}")

        try:
            result = await call_next(context)
            return result

        except Exception as e:
            self.logger.debug(f"[PROXY DEBUG] Error in {method}: {type(e).__name__}: {e}")
            raise

    async def on_notification(
        self,
        context: MiddlewareContext[mt.Notification],
        call_next: CallNext[mt.Notification, Any],
    ) -> Any:
        """Log notification details including progress notifications."""
        notification = context.message
        method = notification.method if hasattr(notification, "method") else "unknown"

        # Only log progress notifications with details, others just basic info
        if method == "notifications/progress":
            params = getattr(notification, "params", None)
            if params:
                progress = getattr(params, "progress", "unknown")
                total = getattr(params, "total", "unknown")
                self.logger.debug(f"[PROXY DEBUG] Progress notification: {progress}/{total}")

        return await call_next(context)

    async def on_call_tool(
        self,
        context: MiddlewareContext[mt.CallToolRequestParams],
        call_next: CallNext[mt.CallToolRequestParams, mt.CallToolResult],
    ) -> mt.CallToolResult:
        """Log tool invocations with timing information."""
        params = context.message
        tool_name = params.name if hasattr(params, "name") else "unknown"

        start_time = time.time()
        self.logger.debug(f"[PROXY DEBUG] TOOL CALL: {tool_name}")

        try:
            result = await call_next(context)
            duration = (time.time() - start_time) * 1000
            self.logger.debug(f"[PROXY DEBUG] Tool {tool_name} completed in {duration:.2f}ms")
            return result

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.logger.debug(f"[PROXY DEBUG] Tool {tool_name} failed after {duration:.2f}ms: {e}")
            raise

    async def on_read_resource(
        self,
        context: MiddlewareContext[mt.ReadResourceRequestParams],
        call_next: CallNext[mt.ReadResourceRequestParams, mt.ReadResourceResult],
    ) -> mt.ReadResourceResult:
        """Log resource access with timing information."""
        params = context.message
        uri = params.uri if hasattr(params, "uri") else "unknown"

        start_time = time.time()
        self.logger.debug(f"[PROXY DEBUG] RESOURCE READ: {uri}")

        try:
            result = await call_next(context)
            duration = (time.time() - start_time) * 1000
            self.logger.debug(f"[PROXY DEBUG] Resource {uri} read in {duration:.2f}ms")
            return result

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.logger.debug(f"[PROXY DEBUG] Resource {uri} failed after {duration:.2f}ms: {e}")
            raise

    async def on_get_prompt(
        self,
        context: MiddlewareContext[mt.GetPromptRequestParams],
        call_next: CallNext[mt.GetPromptRequestParams, mt.GetPromptResult],
    ) -> mt.GetPromptResult:
        """Log prompt execution with timing information."""
        params = context.message
        prompt_name = params.name if hasattr(params, "name") else "unknown"

        start_time = time.time()
        self.logger.debug(f"[PROXY DEBUG] PROMPT GET: {prompt_name}")

        try:
            result = await call_next(context)
            duration = (time.time() - start_time) * 1000
            self.logger.debug(f"[PROXY DEBUG] Prompt {prompt_name} executed in {duration:.2f}ms")
            return result

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.logger.debug(f"[PROXY DEBUG] Prompt {prompt_name} failed after {duration:.2f}ms: {e}")
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


# MCPMUsageTrackingMiddleware removed - functionality moved to MCPMUnifiedTrackingMiddleware


class MCPMUnifiedTrackingMiddleware(Middleware):
    """Unified FastMCP middleware that tracks both individual operations and session-level analytics."""

    def __init__(
        self,
        access_monitor: AccessMonitor,
        server_name: str | None = None,
        action: str = "proxy",
        profile_name: str | None = None,
        transport: SessionTransport = SessionTransport.HTTP,
    ):
        self.monitor = access_monitor
        self.server_name = server_name
        self.action = action
        self.profile_name = profile_name
        self.transport = transport
        self.session_id = str(uuid.uuid4())
        self.session_start_time = None
        self.session_started = False

    async def on_request(self, context, call_next):
        """Handle all requests - track session start on first request and individual operations."""
        # Track session start on first request
        if not self.session_started:
            await self._track_session_start(context)
            self.session_started = True

        # Simply pass through the request - tracking happens in specific methods
        return await call_next(context)

    async def on_call_tool(self, context, call_next):
        """Track tool invocation events with session linking."""
        start_time = time.time()
        tool_name = getattr(context, "tool_name", "unknown")
        server_id = getattr(context, "server_id", "unknown") or self.server_name

        try:
            result = await call_next(context)
            await self.monitor.track_event(
                event_type=AccessEventType.TOOL_INVOCATION,
                server_id=server_id,
                resource_id=tool_name,
                session_id=self.session_id,
                duration_ms=int((time.time() - start_time) * 1000),
                success=True,
                metadata={"middleware": "mcpm", "session_action": self.action},
            )
            return result
        except Exception as e:
            await self.monitor.track_event(
                event_type=AccessEventType.TOOL_INVOCATION,
                server_id=server_id,
                resource_id=tool_name,
                session_id=self.session_id,
                duration_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=str(e),
                metadata={"middleware": "mcpm", "session_action": self.action},
            )
            raise

    async def on_read_resource(self, context, call_next):
        """Track resource access events with session linking."""
        start_time = time.time()
        resource_uri = getattr(context, "resource_uri", "unknown")
        server_id = getattr(context, "server_id", "unknown") or self.server_name

        try:
            result = await call_next(context)
            await self.monitor.track_event(
                event_type=AccessEventType.RESOURCE_ACCESS,
                server_id=server_id,
                resource_id=resource_uri,
                session_id=self.session_id,
                duration_ms=int((time.time() - start_time) * 1000),
                success=True,
                metadata={"middleware": "mcpm", "session_action": self.action},
            )
            return result
        except Exception as e:
            await self.monitor.track_event(
                event_type=AccessEventType.RESOURCE_ACCESS,
                server_id=server_id,
                resource_id=resource_uri,
                session_id=self.session_id,
                duration_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=str(e),
                metadata={"middleware": "mcpm", "session_action": self.action},
            )
            raise

    async def on_get_prompt(self, context, call_next):
        """Track prompt execution events with session linking."""
        start_time = time.time()
        prompt_name = getattr(context, "prompt_name", "unknown")
        server_id = getattr(context, "server_id", "unknown") or self.server_name

        try:
            result = await call_next(context)
            await self.monitor.track_event(
                event_type=AccessEventType.PROMPT_EXECUTION,
                server_id=server_id,
                resource_id=prompt_name,
                session_id=self.session_id,
                duration_ms=int((time.time() - start_time) * 1000),
                success=True,
                metadata={"middleware": "mcpm", "session_action": self.action},
            )
            return result
        except Exception as e:
            await self.monitor.track_event(
                event_type=AccessEventType.PROMPT_EXECUTION,
                server_id=server_id,
                resource_id=prompt_name,
                session_id=self.session_id,
                duration_ms=int((time.time() - start_time) * 1000),
                success=False,
                error_message=str(e),
                metadata={"middleware": "mcpm", "session_action": self.action},
            )
            raise

    async def _track_session_start(self, context):
        """Track session start event."""
        self.session_start_time = time.time()
        server_id = getattr(context, "server_id", None) or self.server_name

        # Collect server and client information
        server_info = self._extract_server_info(context)
        client_info = self._extract_client_info(context)

        # Determine source from client info
        source = SessionSource.LOCAL
        if client_info.get("origin") == "public_internet":
            source = SessionSource.REMOTE

        metadata = {
            "middleware": "mcpm",
            "action": self.action,
            "profile_name": self.profile_name,
            "transport": self.transport.value,
            "source": source.value,
            "server_info": server_info,
            "client_info": client_info,
        }

        await self.monitor.track_event(
            event_type=AccessEventType.SESSION_START,
            server_id=server_id or "unknown",
            resource_id="session",
            session_id=self.session_id,
            success=True,
            metadata=metadata,
        )

    async def track_session_end(self, success: bool = True):
        """Track session end event. Should be called by proxy cleanup."""
        if self.session_start_time is None:
            return  # No session to end

        duration_ms = int((time.time() - self.session_start_time) * 1000)

        metadata = {
            "middleware": "mcpm",
            "action": self.action,
            "profile_name": self.profile_name,
            "transport": self.transport.value,
            "session_duration_ms": duration_ms,
        }

        await self.monitor.track_event(
            event_type=AccessEventType.SESSION_END,
            server_id=self.server_name or "unknown",
            resource_id="session",
            session_id=self.session_id,
            duration_ms=duration_ms,
            success=success,
            metadata=metadata,
        )

    def _extract_server_info(self, context) -> dict:
        """Extract server transport and configuration information."""
        server_info = {}

        # Try to get server configuration from context
        if hasattr(context, "server_config"):
            config = context.server_config
            # Determine transport type based on config attributes
            if hasattr(config, "command"):
                server_info["transport"] = "stdio"
                server_info["command"] = getattr(config, "command", None)
            elif hasattr(config, "url"):
                server_info["transport"] = "http"
                server_info["url"] = getattr(config, "url", None)
            else:
                server_info["transport"] = "unknown"

        # Try to infer from FastMCP server type
        if hasattr(context, "mcp_server"):
            server = context.mcp_server
            server_type = type(server).__name__
            if "stdio" in server_type.lower():
                server_info["transport"] = "stdio"
            elif "remote" in server_type.lower() or "http" in server_type.lower():
                server_info["transport"] = "http"
            server_info["server_type"] = server_type

        # Use the transport from middleware if not detected
        if "transport" not in server_info:
            server_info["transport"] = self.transport.value

        return server_info

    def _extract_client_info(self, context) -> dict:
        """Extract client request origin and information."""
        client_info = {}

        # Try to get request information from context
        request = None
        headers = None

        # Method 1: Try FastMCP's built-in helper
        try:
            from fastmcp.server.dependencies import get_http_headers

            headers = get_http_headers()
        except (RuntimeError, ImportError):
            pass

        # Method 2: Try accessing from context
        if not headers and hasattr(context, "request"):
            request = context.request
            if hasattr(request, "headers"):
                headers = dict(request.headers)

        # Method 3: Try direct context headers
        if not headers and hasattr(context, "headers"):
            headers = dict(context.headers)

        if headers:
            # Extract client IP and origin information
            client_ip = self._get_client_ip(headers, request)
            client_info["ip"] = client_ip
            client_info["origin"] = self._classify_origin(client_ip)

            # Extract User-Agent if available
            user_agent = headers.get("user-agent") or headers.get("User-Agent")
            if user_agent:
                client_info["user_agent"] = user_agent

            # Extract referrer if available
            referrer = headers.get("referer") or headers.get("Referer")
            if referrer:
                client_info["referrer"] = referrer
        else:
            # No HTTP context - likely stdio mode
            client_info["origin"] = "local_stdio"
            client_info["transport"] = "stdio"

        return client_info

    def _get_client_ip(self, headers: dict, request=None) -> str:
        """Extract client IP address from headers."""
        # Check common proxy headers first
        for header in ["x-forwarded-for", "X-Forwarded-For", "x-real-ip", "X-Real-IP"]:
            if header in headers:
                ip = headers[header].split(",")[0].strip()
                if ip:
                    return ip

        # Try to get from request object
        if request and hasattr(request, "client"):
            if hasattr(request.client, "host"):
                return request.client.host

        # Check remote address from headers
        if "remote-addr" in headers or "Remote-Addr" in headers:
            return headers.get("remote-addr") or headers.get("Remote-Addr")

        return "unknown"

    def _classify_origin(self, ip: str) -> str:
        """Classify request origin based on IP address."""
        if not ip or ip == "unknown":
            return "unknown"

        # Local/loopback addresses
        if ip.startswith("127.") or ip == "::1" or ip == "localhost":
            return "local"

        # Private network ranges (RFC 1918)
        private_ranges = [
            "10.",  # 10.0.0.0/8
            "172.16.",
            "172.17.",
            "172.18.",
            "172.19.",  # 172.16.0.0/12 (partial)
            "172.20.",
            "172.21.",
            "172.22.",
            "172.23.",
            "172.24.",
            "172.25.",
            "172.26.",
            "172.27.",
            "172.28.",
            "172.29.",
            "172.30.",
            "172.31.",
            "192.168.",  # 192.168.0.0/16
        ]

        for private_range in private_ranges:
            if ip.startswith(private_range):
                return "local_network"

        # Link-local addresses
        if ip.startswith("169.254."):
            return "link_local"

        # IPv6 private addresses
        if ip.startswith("fd") or ip.startswith("fc"):
            return "local_network"

        # Everything else is public internet
        return "public_internet"
