"""
Router implementation for aggregating multiple MCP servers into a single server.
"""

import logging
import typing as t
from collections import defaultdict
from contextlib import asynccontextmanager

import uvicorn
from mcp import server, types
from mcp.server import InitializationOptions, NotificationOptions
from pydantic import AnyUrl
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.routing import Mount, Route
from starlette.types import AppType

from mcpm.profile.profile_config import ProfileConfigManager
from mcpm.schemas.server_config import ServerConfig

from .client_connection import ServerConnection
from .transport import RouterSseTransport

logger = logging.getLogger(__name__)


TOOL_SPLITOR = "_t_"
RESOURCE_SPLITOR = ":"
RESOURCE_TEMPLATE_SPLITOR = ":"
PROMPT_SPLITOR = "_p_"


class MCPRouter:
    """
    A router that aggregates multiple MCP servers (SSE/STDIO) and
    exposes them as a single SSE server.
    """

    def __init__(self) -> None:
        """Initialize the router."""
        self.server_sessions: t.Dict[str, ServerConnection] = {}
        self.capabilities_mapping: t.Dict[str, t.Dict[str, t.Any]] = defaultdict(dict)
        self.tools_mapping: t.Dict[str, t.Dict[str, t.Any]] = {}
        self.prompts_mapping: t.Dict[str, t.Dict[str, t.Any]] = {}
        self.resources_mapping: t.Dict[str, t.Dict[str, t.Any]] = {}
        self.resources_templates_mapping: t.Dict[str, t.Dict[str, t.Any]] = {}
        self.aggregated_server = self._create_aggregated_server()
        self.profile_manager = ProfileConfigManager()

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
                except Exception as e:
                    # if went wrong, skip the update
                    logger.error(f"Failed to add server {server_config.name}: {e}")

        if server_ids_to_remove:
            for server_id in server_ids_to_remove:
                await self.remove_server(server_id)

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
            # Add tools with namespaced names, preserving existing tools
            self.tools_mapping.update(
                {f"{server_id}{TOOL_SPLITOR}{tool.name}": tool.model_dump() for tool in tools.tools}
            )

        if response.capabilities.prompts:
            prompts = await client.session.list_prompts()  # type: ignore
            # Add prompts with namespaced names, preserving existing prompts
            self.prompts_mapping.update(
                {f"{server_id}{PROMPT_SPLITOR}{prompt.name}": prompt.model_dump() for prompt in prompts.prompts}
            )

        if response.capabilities.resources:
            resources = await client.session.list_resources()  # type: ignore
            # Add resources with namespaced URIs, preserving existing resources
            self.resources_mapping.update(
                {
                    f"{server_id}{RESOURCE_SPLITOR}{resource.uri}": resource.model_dump()
                    for resource in resources.resources
                }
            )
            resources_templates = await client.session.list_resource_templates()  # type: ignore
            # Add resource templates with namespaced URIs, preserving existing templates
            self.resources_templates_mapping.update(
                {
                    f"{server_id}{RESOURCE_TEMPLATE_SPLITOR}{resource_template.uriTemplate}": resource_template.model_dump()
                    for resource_template in resources_templates.resourceTemplates
                }
            )

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
            if key.startswith(f"{server_id}{TOOL_SPLITOR}"):
                self.tools_mapping.pop(key)
        for key in list(self.prompts_mapping.keys()):
            if key.startswith(f"{server_id}{PROMPT_SPLITOR}"):
                self.prompts_mapping.pop(key)
        for key in list(self.resources_mapping.keys()):
            if key.startswith(f"{server_id}{RESOURCE_SPLITOR}"):
                self.resources_mapping.pop(key)
        for key in list(self.resources_templates_mapping.keys()):
            if key.startswith(f"{server_id}{RESOURCE_TEMPLATE_SPLITOR}"):
                self.resources_templates_mapping.pop(key)

    def _patch_handler_func(self, app: server.Server) -> server.Server:
        def get_active_servers(profile: str) -> list[str]:
            servers = self.profile_manager.get_profile(profile) or []
            return [server.name for server in servers]

        def parse_namespaced_id(id_value, splitor):
            """Parse namespaced ID, return server ID and original ID."""
            if splitor in str(id_value):
                return str(id_value).split(splitor, 1)
            return None, None

        def empty_result() -> types.ServerResult:
            return types.ServerResult(types.EmptyResult())

        async def list_prompts(req: types.ListPromptsRequest) -> types.ServerResult:
            prompts: list[types.Prompt] = []
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore
            for server_prompt_id, prompt in self.prompts_mapping.items():
                server_id, _ = parse_namespaced_id(server_prompt_id, PROMPT_SPLITOR)
                if server_id in active_servers:
                    prompt.update({"name": server_prompt_id})
                    prompts.append(types.Prompt(**prompt))
            return types.ServerResult(types.ListPromptsResult(prompts=prompts))

        async def get_prompt(req: types.GetPromptRequest) -> types.ServerResult:
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore

            server_id, prompt_name = parse_namespaced_id(req.params.name, PROMPT_SPLITOR)
            if server_id is None or prompt_name is None:
                return empty_result()

            if server_id not in active_servers:
                return empty_result()

            result = await self.server_sessions[server_id].session.get_prompt(prompt_name, req.params.arguments)
            return types.ServerResult(result)

        async def list_resources(req: types.ListResourcesRequest) -> types.ServerResult:
            resources: list[types.Resource] = []
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore
            for server_resource_id, resource in self.resources_mapping.items():
                server_id, _ = parse_namespaced_id(server_resource_id, RESOURCE_SPLITOR)
                if server_id in active_servers:
                    resource.update({"uri": server_resource_id})
                    resources.append(types.Resource(**resource))
            return types.ServerResult(types.ListResourcesResult(resources=resources))

        async def list_resource_templates(req: types.ListResourceTemplatesRequest) -> types.ServerResult:
            resource_templates: list[types.ResourceTemplate] = []
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore
            for server_resource_template_id, resource_template in self.resources_templates_mapping.items():
                server_id, _ = parse_namespaced_id(server_resource_template_id, RESOURCE_TEMPLATE_SPLITOR)
                if server_id in active_servers:
                    resource_template.update({"uriTemplate": server_resource_template_id})
                    resource_templates.append(types.ResourceTemplate(**resource_template))
            return types.ServerResult(types.ListResourceTemplatesResult(resourceTemplates=resource_templates))

        async def read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore

            server_id, resource_uri = parse_namespaced_id(req.params.uri, RESOURCE_SPLITOR)
            if server_id is None or resource_uri is None:
                return empty_result()
            if server_id not in active_servers:
                return empty_result()

            result = await self.server_sessions[server_id].session.read_resource(AnyUrl(resource_uri))
            return types.ServerResult(result)

        async def list_tools(req: types.ListToolsRequest) -> types.ServerResult:
            tools: list[types.Tool] = []
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore
            for server_tool_id, tool in self.tools_mapping.items():
                server_id, _ = parse_namespaced_id(server_tool_id, TOOL_SPLITOR)
                if server_id in active_servers:
                    tool.update({"name": server_tool_id})
                    tools.append(types.Tool(**tool))

            if not tools:
                return empty_result()

            return types.ServerResult(types.ListToolsResult(tools=tools))

        async def call_tool(req: types.CallToolRequest) -> types.ServerResult:
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore
            logger.info(f"call_tool: {req} with active servers: {active_servers}")

            server_id, tool_name = parse_namespaced_id(req.params.name, TOOL_SPLITOR)
            if server_id is None or tool_name is None:
                return empty_result()
            if server_id not in active_servers:
                return empty_result()

            try:
                result = await self.server_sessions[server_id].session.call_tool(tool_name, req.params.arguments or {})
                return types.ServerResult(result)
            except Exception as e:
                return types.ServerResult(
                    types.CallToolResult(
                        content=[types.TextContent(type="text", text=str(e))],
                        isError=True,
                    ),
                )

        async def complete(req: types.CompleteRequest) -> types.ServerResult:
            active_servers = get_active_servers(req.params.meta.profile)  # type: ignore

            if isinstance(req.params.ref, types.PromptReference):
                server_id, prompt_name = parse_namespaced_id(req.params.ref.name, PROMPT_SPLITOR)
                if server_id is None or prompt_name is None:
                    return empty_result()
                ref = types.PromptReference(name=prompt_name, type="ref/prompt")
            elif isinstance(req.params.ref, types.ResourceReference):
                server_id, resource_uri = parse_namespaced_id(req.params.ref.uri, RESOURCE_SPLITOR)
                if server_id is None or resource_uri is None:
                    return empty_result()
                ref = types.ResourceReference(uri=resource_uri, type="ref/resource")

            if server_id not in active_servers:
                return empty_result()

            result = await self.server_sessions[server_id].session.complete(ref, req.params.argument.model_dump())
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
        # waiting all servers to be initialized
        profiles = self.profile_manager.list_profiles()
        for _, servers in profiles.items():
            for server_config in servers:
                await self.add_server(server_config.name, server_config)

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

        # Create SSE transport
        sse = RouterSseTransport("/messages/")

        # Handle SSE connections
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

        @asynccontextmanager
        async def lifespan(app: AppType):
            yield
            for _, client in self.server_sessions.items():
                if client.healthy():
                    await client.request_for_shutdown()
            logger.info("all alive client sessions have been shut down")

        # Set up middleware for CORS if needed
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

        # Create Starlette app
        app = Starlette(
            debug=False,
            middleware=middleware,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ],
            lifespan=lifespan,
        )

        # Configure and start the server
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="info",
        )
        server_instance = uvicorn.Server(config)
        await server_instance.serve()
