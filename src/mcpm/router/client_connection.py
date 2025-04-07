import asyncio
import logging
from abc import ABC
from contextlib import AsyncExitStack
from typing import Any, Optional

from mcp import ClientSession, InitializeResult, StdioServerParameters, stdio_client
from mcp.client.sse import sse_client

from .connection_types import ConnectionDetails, ConnectionType

logger = logging.getLogger(__name__)


class AbstractMcpClient(ABC):
    session: ClientSession
    _close_event: asyncio.Event
    _exit_stack: AsyncExitStack

    def request_close(self):
        # Set the close event to signal the client to close
        self._close_event.set()

    async def _monitor_close_signal(self):
        await self._close_event.wait()
        try:
            await self._exit_stack.aclose()
        except Exception:
            pass

    async def connect_to_server(self) -> InitializeResult:
        """Connect to an MCP server using the provided connection details.

        Returns:
            InitializeResult: The result of initializing the connection
        """
        raise NotImplementedError

    async def aclose(self):
        raise NotImplementedError


class SSEClient(AbstractMcpClient):
    def __init__(self, connection_details: ConnectionDetails):
        if connection_details.type != ConnectionType.SSE:
            raise ValueError(f"Expected SSE connection type, got {connection_details.type}")
        if not connection_details.url:
            raise ValueError("URL is required for SSE connection")

        self._exit_stack = AsyncExitStack()
        self._close_event = asyncio.Event()
        self._name = f"SSE Client ({connection_details.url})"
        self.session: Optional[ClientSession] = None
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
        # self._client_session = aiohttp.ClientSession()
        # await self._exit_stack.enter_async_context(self._client_session)

        # # Connect to SSE endpoint
        # self._sse_connection = await self._client_session.get(self.connection_details.url)
        # await self._exit_stack.enter_async_context(self._sse_connection)
        read, write = await self._exit_stack.enter_async_context(
            sse_client(self.connection_details.url, headers=self.connection_details.headers)
        )

        # Create MCP client session
        self.session = await self._exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        assert self.session

        response = await self.session.initialize()
        # Start monitoring the close signal
        asyncio.create_task(self._monitor_close_signal())
        return response


class STDIOClient(AbstractMcpClient):
    def __init__(self, connection_details: ConnectionDetails):
        if connection_details.type != ConnectionType.STDIO:
            raise ValueError(f"Expected STDIO connection type, got {connection_details.type}")

        # Initialize session and client objects
        self._exit_stack = AsyncExitStack()
        self._close_event = asyncio.Event()
        self._server_task = None
        self.session: Optional[ClientSession] = None
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

        logger.info(
            f"Connecting to server with command: {self.connection_details.command}, args: {self.connection_details.args}, env: {(self.connection_details.env or {}).keys()}"
        )

        server_params = StdioServerParameters(
            command=self.connection_details.command, args=self.connection_details.args, env=self.connection_details.env
        )

        self.stdio, self.write = await self._exit_stack.enter_async_context(stdio_client(server_params))
        self.session = await self._exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        assert self.session

        result = await self.session.initialize()
        # self._server_task = asyncio.create_task(self._print_error_log())
        asyncio.create_task(self._monitor_close_signal())
        return result

    # async def _print_error_log(self):
    #     # we have to consume the incoming_messages, otherwise it will block our whole system
    #     assert self.session

    #     try:
    #         while 1:
    #             async for message in self.session.incoming_messages:
    #                 if isinstance(message, Exception):
    #                     logger.warning(f"Unable to process stdio: {message}")
    #     except anyio.ClosedResourceError:
    #         logger.info(f"{self.connection_details.id} incoming messages closed")
