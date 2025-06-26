import logging
from collections import defaultdict
from datetime import timedelta
from typing import Any, Dict, List, Literal, Sequence, TextIO

from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    CompleteRequestParams,
    CompleteResult,
    Completion,
    GetPromptRequestParams,
    GetPromptResult,
    ListPromptsResult,
    ListResourcesResult,
    ListResourceTemplatesResult,
    ListToolsResult,
    Prompt,
    PromptReference,
    ReadResourceRequestParams,
    ReadResourceResult,
    Resource,
    ResourceReference,
    ResourceTemplate,
    Tool,
)
from pydantic import AnyUrl

from mcpm.core.router.client_connection import ServerConnection
from mcpm.core.schema import ServerConfig
from mcpm.core.utils.log_manager import ServerLogManager

TOOL_SPLITOR = "_t_"
RESOURCE_SPLITOR = ":"
RESOURCE_TEMPLATE_SPLITOR = ":"
PROMPT_SPLITOR = "_p_"

logger = logging.getLogger(__name__)


class McpRouterCore:
    def __init__(self, on_name_conflict: Literal["strict", "auto"] = "strict"):
        self.server_sessions: Dict[str, ServerConnection] = {}
        self.capabilities_mapping: Dict[str, Dict[str, Any]] = defaultdict(dict)

        self.capabilities_to_server_id: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.tools_mapping: Dict[
            str, Tool
        ] = {}  # tool name -> tool, tool name could be renamed by auto resolve conflict
        self.prompts_mapping: Dict[str, Prompt] = {}
        self.resources_mapping: Dict[str, Resource] = {}
        self.resources_templates_mapping: Dict[str, ResourceTemplate] = {}
        self.error_log_manager = ServerLogManager()
        self.on_name_conflict = on_name_conflict

    @property
    def servers(self) -> List[str]:
        return list(self.server_sessions.keys())

    async def add_server(self, server_id: str, server_config: ServerConfig) -> bool:
        """
        Add a server to the router.

        Args:
            server_id: A unique identifier for the server
            server_config: Server configuration for the server
        """
        if server_id in self.server_sessions:
            raise ValueError(f"Server with ID {server_id} already exists")

        # Create client based on connection type
        errlog: TextIO = self.error_log_manager.open_errlog_file(server_id)
        client = ServerConnection(server_config, errlog=errlog)

        # Connect to the server
        await client.wait_for_initialization()
        if not client.healthy():
            self.error_log_manager.close_errlog_file(server_id)
            raise ValueError(f"Failed to connect to server {server_id}")

        response = client.session_initialized_response
        # Initialize response is MUST in latest protocol
        if response is None:
            self.error_log_manager.close_errlog_file(server_id)
            raise ValueError(f"Failed to connect to server {server_id}")
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
                    if self.on_name_conflict == "strict":
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
                    if self.on_name_conflict == "strict":
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
                    if self.on_name_conflict == "strict":
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
                    if self.on_name_conflict == "strict":
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
        return True

    async def remove_server(self, server_id: str) -> bool:
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
        self.error_log_manager.close_errlog_file(server_id)

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
        return True

    async def update_servers(self, server_configs: Sequence[ServerConfig]) -> bool:
        """
        Update the servers based on the configuration file.

        Args:
            server_configs: List of server configurations
        """
        if not server_configs:
            return True

        current_servers = self.servers
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
        return True

    def get_capability_server_id(
        self, capability_type: Literal["tools", "prompts", "resources", "resource_templates"], id_value: str
    ) -> str | None:
        """Get the server ID associated with a capability ID."""
        return self.capabilities_to_server_id[capability_type].get(id_value)

    def list_tools(self, specified_servers: list[str] | None = None) -> ListToolsResult:
        servers = specified_servers or self.servers
        tools: list[Tool] = []

        for server_tool_id, tool in self.tools_mapping.items():
            server_id = self.get_capability_server_id("tools", server_tool_id)
            if server_id is None:
                continue
            if server_id in servers:
                tools.append(tool.model_copy(update={"name": server_tool_id}))
        return ListToolsResult(tools=tools)

    def list_prompts(self, specified_servers: list[str] | None = None) -> ListPromptsResult:
        servers = specified_servers or self.servers
        prompts: list[Prompt] = []

        for server_prompt_id, prompt in self.prompts_mapping.items():
            server_id = self.get_capability_server_id("prompts", server_prompt_id)
            if server_id is None:
                continue
            if server_id in servers:
                prompts.append(prompt.model_copy(update={"name": server_prompt_id}))
        return ListPromptsResult(prompts=prompts)

    def list_resources(self, specified_servers: list[str] | None = None) -> ListResourcesResult:
        servers = specified_servers or self.servers
        resources: list[Resource] = []

        for server_resource_id, resource in self.resources_mapping.items():
            server_id = self.get_capability_server_id("resources", server_resource_id)
            if server_id is None:
                continue
            if server_id in servers:
                resources.append(resource.model_copy(update={"uri": AnyUrl(server_resource_id)}))
        return ListResourcesResult(resources=resources)

    def list_resource_templates(self, specified_servers: list[str] | None = None) -> ListResourceTemplatesResult:
        servers = specified_servers or self.server_sessions.keys()
        resource_templates: list[ResourceTemplate] = []

        for server_resource_template_id, resource_template in self.resources_templates_mapping.items():
            server_id = self.get_capability_server_id("resource_templates", server_resource_template_id)
            if server_id is None:
                continue
            if server_id in servers:
                resource_templates.append(
                    resource_template.model_copy(update={"uriTemplate": server_resource_template_id})
                )
        return ListResourceTemplatesResult(resourceTemplates=resource_templates)

    async def get_prompt(
        self, params: GetPromptRequestParams, specified_servers: list[str] | None = None
    ) -> GetPromptResult:
        servers = specified_servers or self.servers
        server_id = self.get_capability_server_id("prompts", params.name)
        if server_id is None or server_id not in servers:
            return GetPromptResult(messages=[])
        prompt = self.prompts_mapping.get(params.name)
        if prompt is None:
            return GetPromptResult(messages=[])
        client_session = self.server_sessions.get(server_id)
        if client_session is None or client_session.session is None:
            return GetPromptResult(messages=[])
        result = await client_session.session.get_prompt(prompt.name, params.arguments)
        return result

    async def read_resource(
        self, params: ReadResourceRequestParams, specified_servers: list[str] | None = None
    ) -> ReadResourceResult:
        servers = specified_servers or self.servers
        server_id = self.get_capability_server_id("resources", str(params.uri))
        if server_id is None or server_id not in servers:
            return ReadResourceResult(contents=[])
        resource = self.resources_mapping.get(str(params.uri))
        if resource is None:
            return ReadResourceResult(contents=[])
        client_session = self.server_sessions.get(server_id)
        if client_session is None or client_session.session is None:
            return ReadResourceResult(contents=[])
        result = await client_session.session.read_resource(resource.uri)
        return result

    async def call_tool(
        self,
        params: CallToolRequestParams,
        timeout: timedelta | None = None,
        specified_servers: list[str] | None = None,
    ) -> CallToolResult:
        servers = specified_servers or self.servers
        server_id = self.get_capability_server_id("tools", params.name)
        if server_id is None or server_id not in servers:
            return CallToolResult(content=[], isError=True)
        tool = self.tools_mapping.get(params.name)
        if tool is None:
            return CallToolResult(content=[], isError=True)
        client_session = self.server_sessions.get(server_id)
        if client_session is None or client_session.session is None:
            return CallToolResult(content=[], isError=True)
        result = await client_session.session.call_tool(tool.name, params.arguments, timeout)
        return result

    async def complete(
        self, params: CompleteRequestParams, specified_servers: list[str] | None = None
    ) -> CompleteResult:
        servers = specified_servers or self.servers
        if isinstance(params.ref, PromptReference):
            server_id = self.get_capability_server_id("prompts", params.ref.name)
            if server_id is None or server_id not in servers:
                return CompleteResult(completion=Completion(values=[]))
            prompt = self.prompts_mapping.get(params.ref.name)
            if prompt is None:
                return CompleteResult(completion=Completion(values=[]))
            client_session = self.server_sessions.get(server_id)
            if client_session is None or client_session.session is None:
                return CompleteResult(completion=Completion(values=[]))
            ref = PromptReference(name=prompt.name, type="ref/prompt")

        else:
            server_id = self.get_capability_server_id("resources", str(params.ref.uri))
            if server_id is None or server_id not in servers:
                return CompleteResult(completion=Completion(values=[]))
            resource = self.resources_mapping.get(str(params.ref.uri))
            if resource is None:
                return CompleteResult(completion=Completion(values=[]))
            client_session = self.server_sessions.get(server_id)
            if client_session is None or client_session.session is None:
                return CompleteResult(completion=Completion(values=[]))
            ref = ResourceReference(uri=str(resource.uri), type="ref/resource")

        result = await client_session.session.complete(ref, params.argument.model_dump())
        return result
