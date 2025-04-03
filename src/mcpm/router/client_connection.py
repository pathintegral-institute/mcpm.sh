import asyncio
import logging
from abc import ABC
from contextlib import AsyncExitStack
from typing import Any

import aiohttp
import anyio
from mcp import ClientSession, InitializeResult, StdioServerParameters, stdio_client

from .connection_types import ConnectionDetails, ConnectionType

logger = logging.getLogger(__name__)


class AbstractMcpClient(ABC):
    session: ClientSession

    async def connect_to_server(self) -> InitializeResult:
        """Connect to an MCP server using the provided connection details.

        Returns:
            InitializeResult: The result of initializing the connection
        """
        raise NotImplementedError

    async def aclose(self):
        raise NotImplementedError


class SSEClient(AbstractMcpClient):
    def __init__(self, exit_stack: AsyncExitStack, connection_details: ConnectionDetails):
        if connection_details.type != ConnectionType.SSE:
            raise ValueError(f"Expected SSE connection type, got {connection_details.type}")
        if not connection_details.url:
            raise ValueError("URL is required for SSE connection")

        self._exit_stack = exit_stack
        self._client_session = None
        self._sse_connection = None
        self._name = f"SSE Client ({connection_details.url})"
        self.session = None
        self.connection_details = connection_details

    async def connect_to_server(self) -> InitializeResult:
        """Connect to an MCP server via SSE

        Returns:
            InitializeResult: The result of initializing the connection
        """
        if self.session:
            raise RuntimeError("Server already connected")

        logger.info(f"Connecting to SSE server at {self.connection_details.url}")

        # Create aiohttp client session
        self._client_session = aiohttp.ClientSession()
        await self._exit_stack.enter_async_context(self._client_session)

        # Connect to SSE endpoint
        self._sse_connection = await self._client_session.get(self.connection_details.url)
        await self._exit_stack.enter_async_context(self._sse_connection)

        # Create MCP client session
        self.session = await self._exit_stack.enter_async_context(
            ClientSession(self._sse_connection.content, self._sse_connection.content)
        )
        assert self.session

        return await self.session.initialize()

    async def aclose(self):
        if self.session:
            await self.session.aclose()
            self.session = None
        if self._client_session:
            await self._client_session.close()
            self._client_session = None
        if self._sse_connection:
            await self._sse_connection.close()
            self._sse_connection = None
        logger.info(f"{self._name} closed")


class STDIOClient(AbstractMcpClient):
    def __init__(self, exit_stack: AsyncExitStack, connection_details: ConnectionDetails):
        if connection_details.type != ConnectionType.STDIO:
            raise ValueError(f"Expected STDIO connection type, got {connection_details.type}")
        if not connection_details.command:
            raise ValueError("Command is required for stdio connection")

        # Initialize session and client objects
        self._exit_stack = exit_stack
        self._server_task = None
        self.session = None
        self.connection_details = connection_details

    def _inject_server_env(self, env: dict[str, Any]):
        if not env:
            return {}

        # check if env value is missing
        for key, value in env.items():
            assert value is not None, f"Environment variable {key} is missing"

        return env

    async def connect_to_server(self) -> InitializeResult:
        """Connect to an MCP server

        Returns:
            InitializeResult: The result of initializing the connection
        """
        if self.session:
            raise RuntimeError("Server already connected")

        # For backward compatibility, check if command is a script path
        if not self.connection_details.args and (
            self.connection_details.command.endswith(".py") or self.connection_details.command.endswith(".js")
        ):
            is_python = self.connection_details.command.endswith(".py")
            script_path = self.connection_details.command
            command = "python" if is_python else "node"
            args = [script_path]
        else:
            command = self.connection_details.command
            args = self.connection_details.args or []

        # Handle common executables that might not be in PATH by using full paths
        import shutil

        # Initialize environment if not provided
        env = self._inject_server_env(self.connection_details.env)

        # For node and npx commands, ensure we're using the full path
        if command in ["node", "npx"]:
            cmd_path = shutil.which(command, path=env["PATH"])
            if cmd_path:
                command = cmd_path

        logger.info(f"Connecting to server with command: {command}, args: {args}, env: {env.keys()}")

        server_params = StdioServerParameters(command=command, args=args, env=env)

        self.stdio, self.write = await self._exit_stack.enter_async_context(stdio_client(server_params))
        self.session = await self._exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        assert self.session

        result = await self.session.initialize()
        self._server_task = asyncio.create_task(self._print_error_log())
        return result

    async def _print_error_log(self):
        # we have to consume the incoming_messages, otherwise it will block our whole system
        assert self.session

        try:
            while 1:
                async for message in self.session.incoming_messages:
                    if isinstance(message, Exception):
                        logger.warning(f"Unable to process stdio: {message}")
        except anyio.ClosedResourceError:
            logger.info(f"{self.connection_details.id} incoming messages closed")

    async def aclose(self):
        try:
            if self._server_task and not self._server_task.done():
                task = self._server_task
                self._server_task = None
                task.cancel()
                await task
        except asyncio.CancelledError:
            pass
        logger.info(f"{self.connection_details.id} closed")
