import logging
from collections import defaultdict
from typing import Any, Dict, TextIO, Union

from mcp.server import NotificationOptions
from mcp.types import (
    LoggingCapability,
    Prompt,
    PromptsCapability,
    Resource,
    ResourcesCapability,
    ResourceTemplate,
    ServerCapabilities,
    Tool,
    ToolsCapability,
)
from pydantic import AnyUrl

from mcpm.core.mcp.client_connection import ServerConnection
from mcpm.core.schema import ResourceType, ServerConfig
from mcpm.utils.config import PROMPT_SPLITOR, RESOURCE_SPLITOR, TOOL_SPLITOR
from mcpm.utils.errlog_manager import ServerErrorLogManager

logger = logging.getLogger(__name__)

class MCPClientSessionManager:

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, strict_mode: bool = False) -> None:
        """
        MCPClientSessionManager serves as a central manager for MCP client sessions.

        It manages connections to MCP servers, maintains session health, assembles server capabilities,
        and provides access to tools, prompts, and resources across all registered servers.

        Args:
            strict_mode: If True, raises errors when duplicate capabilities are detected
                         across servers. If False, automatically resolves conflicts by
                         adding server name prefixes.
        """
        self.strict_mode = strict_mode
        self.sessions: Dict[str, ServerConnection] = {}

        self.capabilities_mapping: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.capabilities_to_server_id: Dict[ResourceType, Dict[str, Any]] = defaultdict(dict)
        # real name mapping
        self.tools_mapping: Dict[str, Tool] = {}
        self.prompts_mapping: Dict[str, Prompt] = {}
        self.resources_mapping: Dict[str, Resource] = {}
        self.resources_templates_mapping: Dict[str, ResourceTemplate] = {}
        # error log stream
        self.error_log_manager: ServerErrorLogManager = ServerErrorLogManager()

    def get_alive_sessions(self):
        # returns the server_id list of all alive sessions
        return [server_id for server_id, session in self.sessions.items() if session.healthy()]

    async def _add_session_impl(self, server_id: str, server_config: ServerConfig):
        # initialize session
        if server_id in self.sessions:
            logger.warning(f"Server with ID {server_id} already exists")
            return

        errlog: TextIO = self.error_log_manager.open_errlog_file(server_id)
        client_session = ServerConnection(server_config, errlog=errlog)
        await client_session.wait_for_initialization()

        if not client_session.healthy():
            logger.warning(f"Failed to connect to server {server_id}")
            self.error_log_manager.close_errlog_file(server_id)
            return

        self.sessions[server_id] = client_session

        # update capabilities
        initialized_response = client_session.session_initialized_response
        self.capabilities_mapping[server_id] = initialized_response.capabilities.model_dump()  # type: ignore

        # update tools
        if initialized_response.capabilities.tools: # type: ignore
            await self._assemble_tools(server_id, client_session)
        # update prompts
        if initialized_response.capabilities.prompts: # type: ignore
            await self._assemble_prompts(server_id, client_session)
        # update resources
        if initialized_response.capabilities.resources: # type: ignore
            await self._assemble_resources(server_id, client_session)

    async def add_session(self, server_id: str, server_config: ServerConfig) -> bool:
        try:
            # add log to see whether client session initialization is blocked in this step
            logger.info(f"Ready to add server: {server_config.name}")
            await self._add_session_impl(server_id, server_config)
            logger.info(f"Server {server_config.name} added successfully")
            return True
        except Exception as e:
            # if went wrong, skip the update
            logger.error(f"Failed to add server {server_config.name}: {e}")
            # if error log is opened, close it
            self.error_log_manager.close_errlog_file(server_id)

        return False

    async def remove_session(self, server_id: str):
        if server_id not in self.sessions:
            logger.warning(f"Server with ID {server_id} does not exist")
            return

        client_session = self.sessions.pop(server_id)

        await client_session.request_for_shutdown()

        self.capabilities_mapping.pop(server_id)
        # close error log
        self.error_log_manager.close_errlog_file(server_id)
        # remove all mapping reference
        for key in list(self.tools_mapping.keys()):
            if self.capabilities_to_server_id[ResourceType.TOOL].get(key) == server_id:
                self.tools_mapping.pop(key)
                self.capabilities_to_server_id[ResourceType.TOOL].pop(key)
        for key in list(self.prompts_mapping.keys()):
            if self.capabilities_to_server_id[ResourceType.PROMPT].get(key) == server_id:
                self.prompts_mapping.pop(key)
                self.capabilities_to_server_id[ResourceType.PROMPT].pop(key)
        for key in list(self.resources_mapping.keys()):
            if self.capabilities_to_server_id[ResourceType.RESOURCE].get(key) == server_id:
                self.resources_mapping.pop(key)
                self.capabilities_to_server_id[ResourceType.RESOURCE].pop(key)
        for key in list(self.resources_templates_mapping.keys()):
            if self.capabilities_to_server_id[ResourceType.RESOURCE_TEMPLATE].get(key) == server_id:
                self.resources_templates_mapping.pop(key)
                self.capabilities_to_server_id[ResourceType.RESOURCE_TEMPLATE].pop(key)


    async def update_sessions(self, server_configs: list[ServerConfig]) -> tuple[list[str], list[str]]:
        """
        Update client sessions based on the given server configs.

        Args:
            server_configs: List of server configs to update.

        Returns:
            Tuple of two lists: (server ids added, server ids removed)
        """
        if not server_configs:
            return [], []

        current_servers = self.get_alive_sessions()
        new_servers = [server_config.name for server_config in server_configs]

        server_configs_to_add = [
            server_config for server_config in server_configs if server_config.name not in current_servers
        ]
        server_ids_to_remove = [server_id for server_id in current_servers if server_id not in new_servers]

        if server_configs_to_add:
            for server_config in server_configs_to_add:
                await self.add_session(server_config.name, server_config)

        if server_ids_to_remove:
            for server_id in server_ids_to_remove:
                await self.remove_session(server_id)
                logger.info(f"Server {server_id} removed successfully")

        return [
            server_config.name for server_config in server_configs_to_add
        ], server_ids_to_remove


    async def _assemble_tools(self, server_id: str, client_session: ServerConnection):
        tools = await client_session.session.list_tools() # type: ignore
        for tool in tools.tools:
            tool_name = tool.name
            if tool_name in self.capabilities_to_server_id[ResourceType.TOOL]:
                if self.strict_mode:
                    raise ValueError(
                        f"Tool {tool_name} already exists. Please use unique tool names across all servers."
                    )
                else:
                    # Auto resolve by adding server name prefix
                    tool_name = f"{server_id}{TOOL_SPLITOR}{tool_name}"

            self.capabilities_to_server_id[ResourceType.TOOL][tool_name] = server_id
            self.tools_mapping[tool_name] = tool

    async def _assemble_prompts(self, server_id: str, client_session: ServerConnection):
        prompts = await client_session.session.list_prompts() # type: ignore
        for prompt in prompts.prompts:
            prompt_name = prompt.name
            if prompt_name in self.capabilities_to_server_id[ResourceType.PROMPT]:
                if self.strict_mode:
                    raise ValueError(
                        f"Prompt {prompt_name} already exists. Please use unique prompt names across all servers."
                    )
                else:
                    # Auto resolve by adding server name prefix
                    prompt_name = f"{server_id}{PROMPT_SPLITOR}{prompt_name}"

            self.capabilities_to_server_id[ResourceType.PROMPT][prompt_name] = server_id
            self.prompts_mapping[prompt_name] = prompt

    async def _assemble_resources(self, server_id: str, client_session: ServerConnection):
        resources = await client_session.session.list_resources() # type: ignore
        for resource in resources.resources:
            resource_uri = resource.uri
            if str(resource_uri) in self.capabilities_to_server_id[ResourceType.RESOURCE]:
                if self.strict_mode:
                    raise ValueError(
                        f"Resource {resource_uri} already exists. Please use unique resource names across all servers."
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

            self.capabilities_to_server_id[ResourceType.RESOURCE][str(resource_uri)] = server_id
            self.resources_mapping[str(resource_uri)] = resource

        resource_templates = await client_session.session.list_resource_templates() # type: ignore
        for resource_template in resource_templates.resourceTemplates:
            resource_template_uri_template = resource_template.uriTemplate
            if resource_template_uri_template in self.capabilities_to_server_id[ResourceType.RESOURCE_TEMPLATE]:
                if self.strict_mode:
                    raise ValueError(
                        f"Resource template {resource_template_uri_template} already exists. Please use unique resource template names across all servers."
                    )
                else:
                    # Auto resolve by adding server name prefix
                    resource_template_uri_template = f"{server_id}{RESOURCE_SPLITOR}{resource_template_uri_template}"

            self.capabilities_to_server_id[ResourceType.RESOURCE_TEMPLATE][resource_template_uri_template] = server_id
            self.resources_templates_mapping[resource_template_uri_template] = resource_template

    def get_session(self, server_id: str) -> ServerConnection | None:
        # get the client session by server_id
        return self.sessions.get(server_id)

    def get_capability_server_id(self, resource_type: ResourceType, resource_name: str) -> str | None:
        # get the server_id by resource_type and resource_name
        return self.capabilities_to_server_id[resource_type].get(resource_name)

    def get_resource_schema(self, resource_type: ResourceType, resource_name: str) -> Union[Tool, Prompt, Resource, ResourceTemplate, None]:
        if resource_type == ResourceType.TOOL:
            return self.tools_mapping.get(resource_name)
        elif resource_type == ResourceType.PROMPT:
            return self.prompts_mapping.get(resource_name)
        elif resource_type == ResourceType.RESOURCE:
            return self.resources_mapping.get(resource_name)
        elif resource_type == ResourceType.RESOURCE_TEMPLATE:
            return self.resources_templates_mapping.get(resource_name)
        else:
            return None

    def get_aggregated_server_capabilities(self) -> ServerCapabilities:
        # for initialization of aggregated server
        notification_options = NotificationOptions(
            prompts_changed=False,
            resources_changed=False,
            tools_changed=False,
        )

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

        prompts_capability = (
            PromptsCapability(listChanged=notification_options.prompts_changed) if has_prompts else None
        )
        resources_capability = (
            ResourcesCapability(subscribe=False, listChanged=notification_options.resources_changed)
            if has_resources
            else None
        )
        tools_capability = ToolsCapability(listChanged=notification_options.tools_changed) if has_tools else None
        logging_capability = LoggingCapability() if has_logging else None

        return ServerCapabilities(
            prompts=prompts_capability,
            resources=resources_capability,
            tools=tools_capability,
            logging=logging_capability,
            experimental={},
        )


    async def shutdown(self):
        for session in self.sessions.values():
            await session.request_for_shutdown()

        self.error_log_manager.close_all()
