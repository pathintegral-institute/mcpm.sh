"""
Router implementation for aggregating multiple MCP servers into a single server.
"""

import asyncio
import logging
import typing as t
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Optional

import uvicorn
from deprecated import deprecated
from mcp import server, types
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.types import Lifespan, Receive, Scope, Send

from mcpm.core.router.router import McpRouterCore
from mcpm.core.schema import ServerConfig
from mcpm.monitor.base import AccessEventType, AccessMonitor
from mcpm.monitor.event import trace_event
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.utils.config import (
    MCPM_AUTH_HEADER,
    MCPM_PROFILE_HEADER,
    ConfigManager,
)

from .router_config import RouterConfig
from .transport import RouterSseTransport, patch_meta_data
from .watcher import ConfigWatcher

logger = logging.getLogger(__name__)


class NoOpsResponse(Response):
    def __init__(self):
        super().__init__(content=b"", status_code=204)

    async def __call__(self, scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            }
        )
        await send({"type": "http.response.body", "body": b"", "more_body": False})


class MCPRouter(McpRouterCore):
    """
    A router that aggregates multiple MCP servers (SSE/STDIO) and
    exposes them as a single SSE server.

    Example:
        ```python
        # Initialize with a custom API key
        router = MCPRouter(router_config=RouterConfig(api_key="your-api-key"))

        # Initialize with custom router configuration
        router_config = RouterConfig(
            api_key="your-api-key",
            auth_enabled=True
        )
        router = MCPRouter(router_config=router_config)
        ```
    """

    def __init__(
        self,
        reload_server: bool = False,
        profile_path: str | None = None,
        router_config: RouterConfig | None = None,
    ) -> None:
        """
        Initialize the router.

        :param reload_server: Whether to reload the server when the config changes
        :param profile_path: Path to the profile file
        :param router_config: Optional router configuration to use instead of the global config
        """
        self.aggregated_server = self._create_aggregated_server()
        self.profile_manager = ProfileConfigManager() if profile_path is None else ProfileConfigManager(profile_path)
        self.watcher: Optional[ConfigWatcher] = None
        if reload_server:
            self.watcher = ConfigWatcher(self.profile_manager.profile_path)
        if router_config is None:
            config = ConfigManager().get_router_config()
            router_config = RouterConfig(api_key=config.get("api_key"), auth_enabled=config.get("auth_enabled", False))
        self.router_config = router_config
        super().__init__(on_name_conflict="strict" if router_config and router_config.strict else "auto")

    def get_unique_servers(self) -> list[ServerConfig]:
        profiles = self.profile_manager.list_profiles()
        name_to_server = {server.name: server for server_list in profiles.values() for server in server_list}
        return list(name_to_server.values())

    def _patch_handler_func(self, app: server.Server) -> server.Server:
        def get_target_servers(profile: str) -> list[str] | None:
            if profile == "all":
                return None
            servers = self.profile_manager.get_profile(profile) or []
            return [server.name for server in servers]

        async def list_prompts(req: types.ListPromptsRequest) -> types.ServerResult:
            target_servers = get_target_servers(req.params.meta.profile)  # type: ignore
            result = self.list_prompts(target_servers)
            return types.ServerResult(result)

        @trace_event(AccessEventType.PROMPT_EXECUTION)
        async def get_prompt(req: types.GetPromptRequest) -> types.ServerResult:
            target_servers = get_target_servers(req.params.meta.profile)  # type: ignore
            result = await self.get_prompt(req.params, target_servers)
            return types.ServerResult(result)

        async def list_resources(req: types.ListResourcesRequest) -> types.ServerResult:
            target_servers = get_target_servers(req.params.meta.profile)  # type: ignore
            result = self.list_resources(target_servers)
            return types.ServerResult(result)

        async def list_resource_templates(req: types.ListResourceTemplatesRequest) -> types.ServerResult:
            target_servers = get_target_servers(req.params.meta.profile)  # type: ignore
            result = self.list_resource_templates(target_servers)
            return types.ServerResult(result)

        @trace_event(AccessEventType.RESOURCE_ACCESS)
        async def read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
            target_servers = get_target_servers(req.params.meta.profile)  # type: ignore
            result = await self.read_resource(req.params, target_servers)
            return types.ServerResult(result)

        async def list_tools(req: types.ListToolsRequest) -> types.ServerResult:
            target_servers = get_target_servers(req.params.meta.profile)  # type: ignore
            result = self.list_tools(target_servers)
            return types.ServerResult(result)

        @trace_event(AccessEventType.TOOL_INVOCATION)
        async def call_tool(req: types.CallToolRequest, timeout: timedelta | None = None) -> types.ServerResult:
            target_servers = get_target_servers(req.params.meta.profile)  # type: ignore
            logger.info(f"call_tool: {req} with target servers: {target_servers}")

            try:
                result = await self.call_tool(req.params, timeout, target_servers)
                return types.ServerResult(result)
            except Exception as e:
                logger.error(f"Error calling tool {req.params.name} on server {target_servers}: {e}")
                return types.ServerResult(
                    types.CallToolResult(
                        content=[types.TextContent(type="text", text=str(e))],
                        isError=True,
                    ),
                )

        async def complete(req: types.CompleteRequest) -> types.ServerResult:
            target_servers = get_target_servers(req.params.meta.profile)  # type: ignore
            result = await self.complete(req.params, target_servers)
            return types.ServerResult(result)

        app.request_handlers[types.ListPromptsRequest] = list_prompts
        app.request_handlers[types.GetPromptRequest] = get_prompt
        app.request_handlers[types.ListResourcesRequest] = list_resources
        app.request_handlers[types.ReadResourceRequest] = read_resource
        app.request_handlers[types.ListResourceTemplatesRequest] = list_resource_templates
        app.request_handlers[types.CallToolRequest] = call_tool
        app.request_handlers[types.ListToolsRequest] = list_tools
        app.request_handlers[types.CompleteRequest] = complete

        return app

    def _create_aggregated_server(self) -> server.Server[object]:
        """
        Create an aggregated server that proxies requests to the underlying servers.

        Returns:
            An MCP server instance
        """
        app: server.Server[object] = server.Server(name="mcpm-router", version="1.0.0")
        return self._patch_handler_func(app)

    async def start_watcher_job(self):
        async def reload_servers():
            # reload profile once config file is modified
            self.profile_manager.reload()
            servers_wait_for_update = self.get_unique_servers()
            await self.update_servers(servers_wait_for_update)

        if self.watcher:
            self.watcher.register_modification_callback(reload_servers)
            self.watcher.start()

    async def initialize_router(self):
        """Initialize the router with aggregated servers capabilities."""
        servers_to_start = self.get_unique_servers()
        # load mcp servers sessions
        await self.update_servers(servers_to_start)
        # start a reload watcher job
        await self.start_watcher_job()

    def get_remote_server_app(
        self,
        allow_origins: t.Optional[t.List[str]] = None,
        include_lifespan: bool = True,
        monitor: AccessMonitor | None = None,
    ) -> Starlette:
        """
        Get the remote server app.

        Args:
            allow_origins: List of allowed origins for CORS
            include_lifespan: Whether to include the router's lifespan manager in the app.

        Returns:
            An remote server app
        """
        session_manager = StreamableHTTPSessionManager(
            self.aggregated_server,
            event_store=None,
            stateless=True,
        )

        async def handle_streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
            await session_manager.handle_request(scope, receive, send)

        lifespan_handler: t.Optional[Lifespan[Starlette]] = None
        if include_lifespan:

            @asynccontextmanager
            async def lifespan(app: Starlette):
                async with session_manager.run():
                    try:
                        await self.initialize_router()
                        if monitor:
                            await monitor.initialize_storage()
                        yield
                    except Exception:
                        await self.shutdown()
                        if monitor:
                            await monitor.close()

            lifespan_handler = lifespan

        middleware: t.List[Middleware] = [
            Middleware(
                ProfileMiddleware,
            ),
        ]
        if allow_origins is not None:
            middleware.append(
                Middleware(
                    CORSMiddleware,
                    allow_origins=allow_origins,
                    allow_methods=["*"],
                    allow_headers=["*"],
                ),
            )
        if self.router_config.auth_enabled and self.router_config.api_key is not None:
            middleware.append(
                Middleware(
                    AuthMiddleware,
                    api_key=self.router_config.api_key,
                ),
            )

        app = Starlette(
            debug=False,
            middleware=middleware,
            routes=[
                Mount("/mcp/", app=handle_streamable_http),
            ],
            lifespan=lifespan_handler,
        )
        return app

    @deprecated
    async def get_sse_server_app(
        self, allow_origins: t.Optional[t.List[str]] = None, include_lifespan: bool = True
    ) -> Starlette:
        """
        Get the SSE server app.

        Args:
            allow_origins: List of allowed origins for CORS
            include_lifespan: Whether to include the router's lifespan manager in the app.

        Returns:
            An SSE server app
        """
        await self.initialize_router()

        # Pass the API key to the RouterSseTransport
        api_key = None if not self.router_config.auth_enabled else self.router_config.api_key
        sse = RouterSseTransport("/messages/", api_key=api_key)

        async def handle_sse(request: Request) -> Response:
            try:
                async with sse.connect_sse(
                    request.scope,
                    request.receive,
                    request._send,  # noqa: SLF001
                ) as (read_stream, write_stream):
                    await self.aggregated_server.run(
                        read_stream,
                        write_stream,
                        self.aggregated_server.create_initialization_options(),
                    )
                    # Keep alive while client connected.
                    # EventSourceResponse (inside connect_sse) manages the stream,
                    # but this loop ensures this handler itself stays alive until disconnect.
                    while not await request.is_disconnected():
                        await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Unexpected error in handle_sse (router.py): {e}", exc_info=True)
            finally:
                return NoOpsResponse()

        lifespan_handler: t.Optional[Lifespan[Starlette]] = None
        if include_lifespan:

            @asynccontextmanager
            async def lifespan(app: Starlette):
                yield
                await self.shutdown()

            lifespan_handler = lifespan

        middleware: t.List[Middleware] = []
        if allow_origins is not None:
            middleware.append(
                Middleware(
                    CORSMiddleware,
                    allow_origins=allow_origins,
                    allow_methods=["*"],
                    allow_headers=["*"],
                ),
            )

        app = Starlette(
            debug=False,
            middleware=middleware,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
            lifespan=lifespan_handler,
        )
        return app

    @deprecated
    async def start_sse_server(
        self, host: str = "localhost", port: int = 8080, allow_origins: t.Optional[t.List[str]] = None
    ) -> None:
        """
        Start an SSE server that exposes the aggregated MCP server.

        Args:
            host: The host to bind to
            port: The port to bind to
            allow_origins: List of allowed origins for CORS
        """
        app = await self.get_sse_server_app(allow_origins)

        # Configure and start the server
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
        )
        server_instance = uvicorn.Server(config)
        await server_instance.serve()

    async def start_remote_server(
        self, host: str = "localhost", port: int = 8080, allow_origins: t.Optional[t.List[str]] = None
    ) -> None:
        """
        Start a remote server that exposes the aggregated MCP server.
        Supports both HTTP and SSE.

        Args:
            host: The host to bind to
            port: The port to bind to
            allow_origins: List of allowed origins for CORS
        """
        app = self.get_remote_server_app(allow_origins)

        # Configure and start the server
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
        )
        server_instance = uvicorn.Server(config)
        await server_instance.serve()

    async def shutdown(self):
        if self.watcher:
            await self.watcher.stop()

        # close all client sessions
        for _, client in self.server_sessions.items():
            if client.healthy():
                await client.request_for_shutdown()

        # close all errlog files
        self.error_log_manager.close_all()

        logger.info("all alive client sessions have been shut down")


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: t.Callable[[Scope, Receive, Send], t.Awaitable[None]], api_key: str):
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next: t.Callable[[Request], t.Awaitable[Response]]):
        auth_header = request.headers.get(MCPM_AUTH_HEADER)
        if auth_header is None or auth_header != self.api_key:
            return JSONResponse(status_code=401, content={"error": "Unauthorized"})
        return await call_next(request)


class ProfileMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: t.Callable[[Request], t.Awaitable[Response]]):
        profile = request.headers.get(MCPM_PROFILE_HEADER)
        logger.info(f"Profile middleware: {profile}")
        if profile is None:
            return JSONResponse(status_code=400, content={"error": "Profile is required"})
        body = await request.body()
        logger.info(f"Profile body: {body}")
        body = patch_meta_data(body, profile=profile)
        request._body = body
        logger.info(f"Profile new body: {body}")
        return await call_next(request)
