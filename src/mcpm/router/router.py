"""
Router implementation for aggregating multiple MCP servers into a single server.
"""
import logging
import typing as t
from collections import defaultdict
from typing import Union

import uvicorn
from mcp import server, types
from mcp.server import InitializationOptions, NotificationOptions
from mcp.server.sse import SseServerTransport
from pydantic import AnyUrl
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.routing import Mount, Route

from .client_connection import SSEClient, STDIOClient
from .connection_types import ConnectionDetails, ConnectionType

logger = logging.getLogger(__name__)


class MCPRouter:
    """
    A router that aggregates multiple MCP servers (SSE/STDIO) and
    exposes them as a single SSE server.
    """

    def __init__(self) -> None:
        """Initialize the router."""
        self.server_sessions: t.Dict[str, t.Union[SSEClient, STDIOClient]] = {}
        self.capabilities_mapping: t.Dict[str, t.Dict[str, t.Any]] = defaultdict(dict)
        self.tools_mapping: t.Dict[str, t.Dict[str, t.Any]] = {}
        self.prompts_mapping: t.Dict[str, t.Dict[str, t.Any]] = {}
        self.resources_mapping: t.Dict[str, t.Dict[str, t.Any]] = {}
        self.resources_templates_mapping: t.Dict[str, t.Dict[str, t.Any]] = {}
        self.aggregated_server = self._create_aggregated_server()

    async def update_servers(self, connections: list[ConnectionDetails]):
        """
        Update the servers based on the configuration file.

        Args:
            connections: List of connection details for the servers
        """
        if not connections:
            return

        current_servers = list(self.server_sessions.keys())
        new_servers = [connection.id for connection in connections]

        connection_to_add = [connection for connection in connections if connection.id not in current_servers]
        connection_id_to_remove = [server_id for server_id in current_servers if server_id not in new_servers]

        if connection_to_add:
            for connection in connection_to_add:
                try:
                    logger.info(f"Adding server {connection.id}")
                    await self.add_server(connection.id, connection)
                except Exception as e:
                    # if went wrong, skip the update
                    logger.error(f"Failed to add server {connection.id}: {e}")

        if connection_id_to_remove:
            for server_id in connection_id_to_remove:
                logger.info(f"Removing server {server_id}")
                await self.remove_server(server_id)

    async def add_server(self, server_id: str, connection: ConnectionDetails) -> None:
        """
        Add a server to the router.

        Args:
            server_id: A unique identifier for the server
            connection: Connection details for the server
        """
        if server_id in self.server_sessions:
            raise ValueError(f"Server with ID {server_id} already exists")

        # Create client based on connection type
        if connection.type == ConnectionType.SSE:
            client = SSEClient(connection)
        elif connection.type == ConnectionType.STDIO:
            # Create a new AsyncExitStack for this client
            client = STDIOClient(connection)
        else:
            raise ValueError(f"Unsupported connection type: {connection.type}")

        # Connect to the server
        response = await client.connect_to_server()
        logger.info(f"Connected to server {server_id} with capabilities: {response.capabilities}")

        # Store the session
        self.server_sessions[server_id] = client

        # Store the capabilities for this server
        self.capabilities_mapping[server_id] = response.capabilities.model_dump()

        # Collect server tools, prompts, and resources
        if response.capabilities.tools:
            tools = await client.session.list_tools() # type: ignore
            # Add tools with namespaced names, preserving existing tools
            self.tools_mapping.update({f"{server_id}.{tool.name}": tool.model_dump() for tool in tools.tools})

        if response.capabilities.prompts:
            prompts = await client.session.list_prompts()  # type: ignore
            # Add prompts with namespaced names, preserving existing prompts
            self.prompts_mapping.update(
                {f"{server_id}.{prompt.name}": prompt.model_dump() for prompt in prompts.prompts}
            )

        if response.capabilities.resources:
            resources = await client.session.list_resources()  # type: ignore
            # Add resources with namespaced URIs, preserving existing resources
            self.resources_mapping.update(
                {f"{server_id}:{resource.uri}": resource.model_dump() for resource in resources.resources}
            )
            resources_templates = await client.session.list_resource_templates()  # type: ignore
            # Add resource templates with namespaced URIs, preserving existing templates
            self.resources_templates_mapping.update(
                {f"{server_id}:{resource_template.uriTemplate}": resource_template.model_dump() for resource_template in resources_templates.resourceTemplates}
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
        logger.info(f"server_sessions: {self.server_sessions}")
        client = self.server_sessions[server_id]
        client.request_close()
        logger.info(f"server_sessions after close: {self.server_sessions}")

        # Remove the server from all collections
        del self.server_sessions[server_id]
        del self.capabilities_mapping[server_id]

        # Delete registered tools, resources and prompts
        for key in list(self.tools_mapping.keys()):
            if key.startswith(f"{server_id}."):
                self.tools_mapping.pop(key)
        for key in list(self.prompts_mapping.keys()):
            if key.startswith(f"{server_id}."):
                self.prompts_mapping.pop(key)
        for key in list(self.resources_mapping.keys()):
            if key.startswith(f"{server_id}:"):
                self.resources_mapping.pop(key)
        for key in list(self.resources_templates_mapping.keys()):
            if key.startswith(f"{server_id}:"):
                self.resources_templates_mapping.pop(key)

    def _create_aggregated_server(self) -> server.Server[object]:
        """
        Create an aggregated server that proxies requests to the underlying servers.

        Returns:
            An MCP server instance
        """
        app: server.Server[object] = server.Server(name="mcpm-router")

        # Define request handlers

        # List prompts handler
        async def _list_prompts(_: t.Any) -> types.ServerResult:
            all_prompts = []
            for server_prompt_id, prompts in self.prompts_mapping.items():
                prompts.update({"name": server_prompt_id})
                all_prompts.append(types.Prompt(**prompts))
            return types.ServerResult(types.ListPromptsResult(prompts=all_prompts))

        app.request_handlers[types.ListPromptsRequest] = _list_prompts

        # Get prompt handler
        async def _get_prompt(req: types.GetPromptRequest) -> types.ServerResult:
            prompt_name = req.params.name

            # Parse server_id from namespaced prompt name
            if "." in prompt_name:
                server_id, original_name = prompt_name.split(".", 1)
                if server_id in self.server_sessions:
                    result = await self.server_sessions[server_id].session.get_prompt(
                        original_name, req.params.arguments
                    )
                    return types.ServerResult(result)

            # Return error if prompt not found
            return types.ServerResult(types.EmptyResult())

        app.request_handlers[types.GetPromptRequest] = _get_prompt

        # List resources handler
        async def _list_resources(_: t.Any) -> types.ServerResult:
            all_resources = []
            for server_resource_id, resource in self.resources_mapping.items():
                resource.update({"uri": server_resource_id})
                all_resources.append(types.Resource(**resource))
            return types.ServerResult(types.ListResourcesResult(resources=all_resources))

        app.request_handlers[types.ListResourcesRequest] = _list_resources

        # List resource templates handler
        async def _list_resource_templates(_: t.Any) -> types.ServerResult:
            all_resource_templates = []
            for server_resource_template_id, resource_template in self.resources_templates_mapping.items():
                resource_template.update({"uriTemplate": server_resource_template_id})
                all_resource_templates.append(types.ResourceTemplate(**resource_template))
            return types.ServerResult(types.ListResourceTemplatesResult(resourceTemplates=all_resource_templates))

        app.request_handlers[types.ListResourceTemplatesRequest] = _list_resource_templates

        # Read resource handler
        async def _read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
            resource_uri = req.params.uri

            # Parse server_id from namespaced resource URI
            if ":" in str(resource_uri):
                server_id, original_uri = str(resource_uri).split(":", 1)
                if server_id in self.server_sessions:
                    result = await self.server_sessions[server_id].session.read_resource(AnyUrl(original_uri))
                    return types.ServerResult(result)

            # Return error if resource not found
            return types.ServerResult(types.EmptyResult())

        app.request_handlers[types.ReadResourceRequest] = _read_resource

        # List tools handler
        async def _list_tools(_: t.Any) -> types.ServerResult:
            all_tools = []
            logger.info(f"Listing tools: {self.tools_mapping}")
            for tool_name, tool_data in self.tools_mapping.items():
                # Create tool object directly from the data
                tool = types.Tool(**tool_data)
                tool.name = tool_name
                all_tools.append(tool)
            return types.ServerResult(types.ListToolsResult(tools=all_tools))

        app.request_handlers[types.ListToolsRequest] = _list_tools

        # Call tool handler
        async def _call_tool(req: types.CallToolRequest) -> types.ServerResult:
            tool_name = req.params.name

            # Parse server_id from namespaced tool name
            if "." in tool_name:
                server_id, original_name = tool_name.split(".", 1)
                if server_id in self.server_sessions:
                    try:
                        result = await self.server_sessions[server_id].session.call_tool(
                            original_name, req.params.arguments or {}
                        )
                        return types.ServerResult(result)
                    except Exception as e:
                        return types.ServerResult(
                            types.CallToolResult(
                                content=[types.TextContent(type="text", text=str(e))],
                                isError=True,
                            ),
                        )

            # Return error if tool not found
            return types.ServerResult(
                types.CallToolResult(
                    content=[types.TextContent(type="text", text=f"Tool not found: {tool_name}")],
                    isError=True,
                ),
            )

        app.request_handlers[types.CallToolRequest] = _call_tool

        # Complete handler
        async def _complete(req: types.CompleteRequest) -> types.ServerResult:
            ref = req.params.ref

            # distinguish ref to resource reference and prompt reference
            ref: Union[types.ResourceReference, types.PromptReference]
            if isinstance(ref, types.ResourceReference):
                server_id, resource_uri = str(ref.uri).split(":", 1)
                ref = types.ResourceReference(uri=resource_uri, type="ref/resource")
            else:
                server_id, prompt_name = ref.name.split(".", 1)
                ref = types.PromptReference(name=prompt_name, type="ref/prompt")

            if server_id in self.server_sessions:
                result = await self.server_sessions[server_id].session.complete(
                    ref,
                    req.params.argument.model_dump(),
                )
                return types.ServerResult(result)

            # Return error if reference not found
            return types.ServerResult(
                types.CallToolResult(
                    content=[types.TextContent(type="text", text=f"Reference not found: {ref}")],
                    isError=True,
                ),
            )

        app.request_handlers[types.CompleteRequest] = _complete

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
        sse = SseServerTransport("/messages/")

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
