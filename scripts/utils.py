from contextlib import AsyncExitStack
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.exceptions import McpError
from mcp.types import ListPromptsResult, ListResourcesResult, ListToolsResult


class McpClient:
    session: ClientSession

    def __init__(self):
        self.exit_stack = AsyncExitStack()

    async def connect_to_server(self, cmd, args, env):
        command = cmd
        server_params = StdioServerParameters(command=command, args=args, env=env)

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write, read_timeout_seconds=timedelta(seconds=60))
        )

        await self.session.initialize()

    async def list_tools(self):
        # List available tools
        try:
            tools_result = await self.session.list_tools()
            return tools_result
        except McpError:
            return ListToolsResult(tools=[])

    async def list_prompts(self):
        # List available prompts
        try:
            prompts_result = await self.session.list_prompts()
            return prompts_result
        except McpError:
            return ListPromptsResult(prompts=[])

    async def list_resources(self):
        # List available resources
        try:
            resources_result = await self.session.list_resources()
            return resources_result
        except McpError:
            return ListResourcesResult(resources=[])

    async def close(self):
        await self.exit_stack.aclose()
