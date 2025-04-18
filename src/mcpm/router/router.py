"""
Router implementation for aggregating multiple MCP servers into a single server.
"""

import logging
import typing as t
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import Literal, Optional

import uvicorn
from mcp import server, types
from mcp.server import InitializationOptions, NotificationOptions
from pydantic import AnyUrl
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.routing import Mount, Route
from starlette.types import AppType, Lifespan

from mcpm.monitor.base import AccessEventType
from mcpm.monitor.event import trace_event
from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.schemas.server_config import ServerConfig
from mcpm.utils.config import PROMPT_SPLITOR, RESOURCE_SPLITOR, RESOURCE_TEMPLATE_SPLITOR, TOOL_SPLITOR

from .client_connection import ServerConnection
from .transport import RouterSseTransport
from .watcher import ConfigWatcher

logger = logging.getLogger(__name__)


class MCPRouter:
    """
    A router that aggregates multiple MCP servers (SSE/STDIO) and
    exposes them as a single SSE server.
    """

    def __init__(self, reload_server: bool = False, profile_path: str | None = None, strict: bool = False) -> None:
        """
        Initialize the router.

        :param reload_server: Whether to reload the server when the config changes
        :param profile_path: Path to the profile file
        :param strict: Whether to use strict mode for duplicated tool name.
                       If True, raise error when duplicated tool name is found else auto resolve by adding server name prefix
        """
        self.server_sessions: t.Dict[str, ServerConnection] = {}
        self.capabilities_mapping: t.Dict[str, t.Dict[str, t.Any]] = defaultdict(dict)
        self.capabilities_to_server_id: t.Dict[str, t.Dict[str, t.Any]] = defaultdict(dict)
        self.tools_mapping: t.Dict[str, types.Tool] = {}
        self.prompts_mapping: t.Dict[str, types.Prompt] = {}
        self.resources_mapping: t.Dict[str, types.Resource] = {}
        self.resources_templates_mapping: t.Dict[str, types.ResourceTemplate] = {}
        self.aggregated_server = self._create_aggregated_server()
        self.profile_manager = ProfileConfigManager() if profile_path is None else ProfileConfigManager(profile_path)
        self.watcher: Optional[ConfigWatcher] = None
        if reload_server:
            self.watcher = ConfigWatcher(self.profile_manager.profile_path)
        self.strict: bool = strict

    def get_unique_servers(self) -> list[ServerConfig]:
        profiles = self.profile_manager.list_profiles()
        name_to_server = {server.name: server for server_list in profiles.values() for server in server_list}
        return list(name_to_server.values())

    async def update_servers(self, server_configs: list[ServerConfig]):
        """
        Update the servers based on the configuration file.

        Args:
            server_configs: List of server configurations
        """
        if not server_configs:
            return

        current_servers = list(self.server_sessions.keys())
        new_servers = [server_config.name for server_config in server_configs]

        server_configs_to_add = [
            server_config for server_config in server_configs if server_config.name not in current_servers
        ]
        server_ids_to_remove = [server_id for server_id in current_servers if server_id not in new_servers]

        if server_configs_to_add:
            for server_config in server_configs_to_add:
                try:
                    await self.add_server(server_config.name, server_config)
                    logger.info(f"Server {server_config.name} added successfully")
                except Exception as e:
                    # if went wrong, skip the update
                    logger.error(f"Failed to add server {server_config.name}: {e}")

        if server_ids_to_remove:
            for server_id in server_ids_to_remove:
                await self.remove_server(server_id)
                logger.info(f"Server {server_id} removed successfully")

    async def add_server(self, server_id: str, server_config: ServerConfig) -> None:
        """
        Add a server to the router.

        Args:
            server_id: A unique identifier for the server
            server_config: Server configuration for the server
        """
        if server_id in self.server_sessions:
            raise ValueError(f"Server with ID {server_id} already exists")

        # Create client based on connection type
        client = ServerConnection(server_config)

        # Connect to the server
        await client.wait_for_initialization()
        if not client.healthy():
            raise ValueError(f"Failed to connect to server {server_id}")

        response = client.session_initialized_response
        logger.info(f"Connected to server {server_id} with capabilities: {response.capabilities}")

        # Store the session
        self.server_sessions[server_id] = client

        # Store the capabilities for this server
        self.capabilities_mapping[server_id] = response.capabilities.model_dump()

        # Collect server tools, prompts, and resources
        if response.capabilities.tools:
            tools = await client.session.list_tools()  # type: ignore
            for tool in tools.tools:
                # To make sure tool name is unique across all servers
                tool_name = tool.name
                if tool_name in self.capabilities_to_server_id["tools"]:
                    if self.strict:
                        raise ValueError(
                            f"Tool {tool_name} already exists. Please use unique tool names across all servers."
                        )
                    else:
                        # Auto resolve by adding server name prefix
                        tool_name = f"{server_id}{TOOL_SPLITOR}{tool_name}"
                self.capabilities_to_server_id["tools"][tool_name] = server_id
                self.tools_mapping[tool_name] = tool

        if response.capabilities.prompts:
            prompts = await client.session.list_prompts()  # type: ignore
            for prompt in prompts.prompts:
                # To make sure prompt name is unique across all servers
                prompt_name = prompt.name
                if prompt_name in self.capabilities_to_server_id["prompts"]:
                    if self.strict:
                        raise ValueError(
                            f"Prompt {prompt_name} already exists. Please use unique prompt names across all servers."
                        )
                    else:
                        # Auto resolve by adding server name prefix
                        prompt_name = f"{server_id}{PROMPT_SPLITOR}{prompt_name}"
                self.prompts_mapping[prompt_name] = prompt
                self.capabilities_to_server_id["prompts"][prompt_name] = server_id

        if response.capabilities.resources:
            resources = await client.session.list_resources()  # type: ignore
            for resource in resources.resources:
                # To make sure resource URI is unique across all servers
                resource_uri = resource.uri
                if str(resource_uri) in self.capabilities_to_server_id["resources"]:
                    if self.strict:
                        raise ValueError(
                            f"Resource {resource_uri} already exists. Please use unique resource URIs across all servers."
                        )
                    else:
                        # Auto resolve by adding server name prefix
                        host = resource_uri.host
                        resource_uri = AnyUrl.build(
                            host=f"{server_id}{RESOURCE_SPLITOR}{host}",
                            scheme=resource_uri.scheme,
                            path=resource_uri.path,
                            username=resource_uri.username,
                            password=resource_uri.password,
                            port=resource_uri.port,
                            query=resource_uri.query,
                            fragment=resource_uri.fragment,
                        )
                self.resources_mapping[str(resource_uri)] = resource
                self.capabilities_to_server_id["resources"][str(resource_uri)] = server_id
            resources_templates = await client.session.list_resource_templates()  # type: ignore
            for resource_template in resources_templates.resourceTemplates:
                # To make sure resource template URI is unique across all servers
                resource_template_uri_template = resource_template.uriTemplate
                if resource_template_uri_template in self.capabilities_to_server_id["resource_templates"]:
                    if self.strict:
                        raise ValueError(
                            f"Resource template {resource_template_uri_template} already exists. Please use unique resource template URIs across all servers."
                        )
                    else:
                        # Auto resolve by adding server name prefix
                        resource_template_uri_template = (
                            f"{server_id}{RESOURCE_TEMPLATE_SPLITOR}{resource_template.uriTemplate}"
                        )
                self.resources_templates_mapping[resource_template_uri_template] = resource_template
                self.capabilities_to_server_id["resource_templates"][resource_template_uri_template] = server_id

    async def remove_server(self, server_id: str) -> None:
        """
        Remove a server from the router.

        Args:
            server_id: The ID of the server to remove
        """
        if server_id not in self.server_sessions:
            raise ValueError(f"Server with ID {server_id} does not exist")

        # Close the client session
        client = self.server_sessions[server_id]
        await client.request_for_shutdown()

        # Remove the server from all collections
        del self.server_sessions[server_id]
        del self.capabilities_mapping[server_id]

        # Delete registered tools, resources and prompts
        for key in list(self.tools_mapping.keys()):
            if self.capabilities_to_server_id["tools"].get(key) == server_id:
                self.tools_mapping.pop(key)
                self.capabilities_to_server_id["tools"].pop(key)
        for key in list(self.prompts_mapping.keys()):
            if self.capabilities_to_server_id["prompts"].get(key) == server_id:
                self.prompts_mapping.pop(key)
                self.capabilities_to_server_id["prompts"].pop(key)
        for key in list(self.resources_mapping.keys()):
            if self.capabilities_to_server_id["resources"].get(key) == server_id:
                self.resources_mapping.pop(key)
                self.capabilities_to_server_id["resources"].pop(key)
        for key in list(self.resources_templates_mapping.keys()):
            if self.capabilities_to_server_id["resource_templates"].get(key) == server_id:
                self.resources_templates_mapping.pop(key)
                self.capabilities_to_server_id["resource_templates"].pop(key)

    def _patch_handler_func(self, app: server.Server) -> server.Server:
        def get_active_servers(profile: str) -> list[str]:
            servers = self.profile_manager.get_profile(profile) or []
            return [server.name for server in servers]

        def get_capability_server_id(
            capability_type: Literal["tools", "prompts", "resources", "resource_templates"], id_value: str
        ) -> str | None:
            """Get the server ID associated with a capability ID."""
            return self.capabilities_to_server_id[capability_type].get(id_value)

        def empty_result() -> types.ServerResult:
            return types.ServerResult(types.EmptyResult())

        async def list_prompts(req: types.ListPromptsRequest) -> types.ServerResult:
            prompts: list[types.Prompt] = []
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore
            for server_prompt_id, prompt in self.prompts_mapping.items():
                server_id = get_capability_server_id("prompts", server_prompt_id)
                if server_id in active_servers:
                    prompts.append(prompt.model_copy(update={"name": server_prompt_id}))
            return types.ServerResult(types.ListPromptsResult(prompts=prompts))

        @trace_event(AccessEventType.PROMPT_EXECUTION)
        async def get_prompt(req: types.GetPromptRequest) -> types.ServerResult:
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore

            server_id = get_capability_server_id("prompts", req.params.name)
            if server_id is None:
                return empty_result()

            if server_id not in active_servers:
                return empty_result()
            prompt = self.prompts_mapping.get(req.params.name)
            if prompt is None:
                return empty_result()
            result = await self.server_sessions[server_id].session.get_prompt(prompt.name, req.params.arguments)
            return types.ServerResult(result)

        async def list_resources(req: types.ListResourcesRequest) -> types.ServerResult:
            resources: list[types.Resource] = []
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore
            for server_resource_id, resource in self.resources_mapping.items():
                server_id = get_capability_server_id("resources", server_resource_id)
                if server_id is None:
                    continue
                if server_id in active_servers:
                    resources.append(resource.model_copy(update={"uri": AnyUrl(server_resource_id)}))
            return types.ServerResult(types.ListResourcesResult(resources=resources))

        async def list_resource_templates(req: types.ListResourceTemplatesRequest) -> types.ServerResult:
            resource_templates: list[types.ResourceTemplate] = []
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore
            for server_resource_template_id, resource_template in self.resources_templates_mapping.items():
                server_id = get_capability_server_id("resource_templates", server_resource_template_id)
                if server_id is None:
                    continue
                if server_id in active_servers:
                    resource_templates.append(
                        resource_template.model_copy(update={"uriTemplate": server_resource_template_id})
                    )
            return types.ServerResult(types.ListResourceTemplatesResult(resourceTemplates=resource_templates))

        @trace_event(AccessEventType.RESOURCE_ACCESS)
        async def read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore

            server_id = get_capability_server_id("resources", str(req.params.uri))
            if server_id is None:
                return empty_result()
            if server_id not in active_servers:
                return empty_result()
            resource = self.resources_mapping.get(str(req.params.uri))
            if resource is None:
                return empty_result()

            result = await self.server_sessions[server_id].session.read_resource(resource.uri)
            return types.ServerResult(result)

        async def list_tools(req: types.ListToolsRequest) -> types.ServerResult:
            tools: list[types.Tool] = []
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore
            for server_tool_id, tool in self.tools_mapping.items():
                server_id = get_capability_server_id("tools", server_tool_id)
                if server_id is None:
                    continue
                if server_id in active_servers:
                    tools.append(tool.model_copy(update={"name": server_tool_id}))

            if not tools:
                return empty_result()

            return types.ServerResult(types.ListToolsResult(tools=tools))

        @trace_event(AccessEventType.TOOL_INVOCATION)
        async def call_tool(req: types.CallToolRequest) -> types.ServerResult:
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore
            logger.info(f"call_tool: {req} with active servers: {active_servers}")

            tool_name = req.params.name
            server_id = get_capability_server_id("tools", tool_name)
            if server_id is None:
                logger.debug(f"call_tool: {req} with tool_name: {tool_name}. Server ID {server_id} is not found")
                return empty_result()
            if server_id not in active_servers:
                logger.debug(
                    f"call_tool: {req} with tool_name: {tool_name}. Server ID {server_id} is not in active servers"
                )
                return empty_result()
            tool = self.tools_mapping.get(tool_name)
            if tool is None:
                return empty_result()

            try:
                result = await self.server_sessions[server_id].session.call_tool(tool.name, req.params.arguments or {})
                return types.ServerResult(result)
            except Exception as e:
                logger.error(f"Error calling tool {tool_name} on server {server_id}: {e}")
                return types.ServerResult(
                    types.CallToolResult(
                        content=[types.TextContent(type="text", text=str(e))],
                        isError=True,
                    ),
                )

        async def complete(req: types.CompleteRequest) -> types.ServerResult:
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore

            if isinstance(req.params.ref, types.PromptReference):
                server_id = get_capability_server_id("prompts", req.params.ref.name)
                if server_id is None:
                    return empty_result()
                if server_id not in active_servers:
                    return empty_result()
                prompt = self.prompts_mapping.get(req.params.ref.name)
                if prompt is None:
                    return empty_result()
                ref = types.PromptReference(name=prompt.name, type="ref/prompt")
            elif isinstance(req.params.ref, types.ResourceReference):
                server_id = get_capability_server_id("resources", str(req.params.ref.uri))
                if server_id is None:
                    return empty_result()
                resource = self.resources_mapping.get(str(req.params.ref.uri))
                if resource is None:
                    return empty_result()
                ref = types.ResourceReference(uri=str(resource.uri), type="ref/resource")

            if server_id not in active_servers:
                return empty_result()

            result = await self.server_sessions[server_id].session.complete(ref, req.params.arguments or {})
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
        app: server.Server[object] = server.Server(name="mcpm-router")
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
        # initialize server capabilities with all servers loaded
        await self._initialize_server_capabilities()

    async def _initialize_server_capabilities(self):
        """Initialize the server capabilities."""
        # Create notification options
        notification_options = NotificationOptions(
            prompts_changed=True,
            resources_changed=True,
            tools_changed=True,
        )

        # Prepare capabilities
        has_prompts = any(
            server_capabilities.get("prompts") for server_capabilities in self.capabilities_mapping.values()
        )
        has_resources = any(
            server_capabilities.get("resources") for server_capabilities in self.capabilities_mapping.values()
        )
        has_tools = any(server_capabilities.get("tools") for server_capabilities in self.capabilities_mapping.values())
        has_logging = any(
            server_capabilities.get("logging") for server_capabilities in self.capabilities_mapping.values()
        )

        # Create capability objects as needed
        prompts_capability = (
            types.PromptsCapability(listChanged=notification_options.prompts_changed) if has_prompts else None
        )
        resources_capability = (
            types.ResourcesCapability(subscribe=False, listChanged=notification_options.resources_changed)
            if has_resources
            else None
        )
        tools_capability = types.ToolsCapability(listChanged=notification_options.tools_changed) if has_tools else None
        logging_capability = types.LoggingCapability() if has_logging else None

        # Create server capabilities
        capabilities = types.ServerCapabilities(
            prompts=prompts_capability,
            resources=resources_capability,
            tools=tools_capability,
            logging=logging_capability,
            experimental={},
        )

        # Set initialization options
        self.aggregated_server.initialization_options = InitializationOptions(
            server_name="mcpm-router",
            server_version="1.0.0",
            capabilities=capabilities,
        )

    async def get_sse_server_app(
        self, allow_origins: t.Optional[t.List[str]] = None, include_lifespan: bool = True
    ) -> AppType:
        """
        Get the SSE server app.

        Args:
            allow_origins: List of allowed origins for CORS
            include_lifespan: Whether to include the router's lifespan manager in the app.

        Returns:
            An SSE server app
        """
        await self.initialize_router()

        sse = RouterSseTransport("/messages/")

        async def handle_sse(request: Request) -> None:
            async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
            ) as (read_stream, write_stream):
                await self.aggregated_server.run(
                    read_stream,
                    write_stream,
                    self.aggregated_server.initialization_options,
                )

        lifespan_handler: t.Optional[Lifespan[AppType]] = None
        if include_lifespan:

            @asynccontextmanager
            async def lifespan(app: AppType):
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

    async def shutdown(self):
        if self.watcher:
            await self.watcher.stop()

        # close all client sessions
        for _, client in self.server_sessions.items():
            if client.healthy():
                await client.request_for_shutdown()

        logger.info("all alive client sessions have been shut down")
