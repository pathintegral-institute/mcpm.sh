import asyncio
import logging
from typing import (
    Optional,
    TextIO,
    cast,
)

from httpx import HTTPStatusError
from mcp import ClientSession, InitializeResult, StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import streamablehttp_client

from mcpm.core.schema import RemoteServerConfig, ServerConfig, STDIOServerConfig

logger = logging.getLogger(__name__)


def _stdio_transport_context(server_config: ServerConfig, errlog: TextIO):
    server_config = cast(STDIOServerConfig, server_config)
    server_params = StdioServerParameters(command=server_config.command, args=server_config.args, env=server_config.env)
    return stdio_client(server_params, errlog=errlog)


def _sse_transport_context(server_config: ServerConfig):
    server_config = cast(RemoteServerConfig, server_config)
    return sse_client(server_config.url, headers=server_config.headers)


def _streamable_http_transport_context(server_config: ServerConfig):
    server_config = cast(RemoteServerConfig, server_config)
    return streamablehttp_client(server_config.url, headers=server_config.headers)


class ServerConnection:
    def __init__(self, server_config: ServerConfig, errlog: TextIO) -> None:
        self.session: Optional[ClientSession] = None
        self.session_initialized_response: Optional[InitializeResult] = None
        self._initialized = False
        self.server_config = server_config
        self._initialized_event = asyncio.Event()
        self._shutdown_event = asyncio.Event()
        self._errlog = errlog

        self._server_task = asyncio.create_task(self._server_lifespan_cycle())

    def _transport_context_factory(self, server_config: ServerConfig):
        if isinstance(server_config, STDIOServerConfig):
            return _stdio_transport_context(server_config, self._errlog)
        elif isinstance(server_config, RemoteServerConfig):
            return _streamable_http_transport_context(server_config)
        else:
            raise ValueError(f"Custom server config {server_config.name} is not supported for router proxy")

    def healthy(self) -> bool:
        return self.session is not None and self._initialized

    # block until client session is initialized
    async def wait_for_initialization(self):
        await self._initialized_event.wait()

    # request for client session to gracefully close
    async def request_for_shutdown(self):
        self._shutdown_event.set()

    # block until client session is shutdown
    async def wait_for_shutdown_request(self):
        await self._shutdown_event.wait()

    async def _connect_to_server(self, transport):  # The type is too complex to be inferred
        async with transport as (read, write, *_):
            async with ClientSession(read, write) as session:
                self.session_initialized_response = await session.initialize()

                self.session = session
                self._initialized = True
                self._initialized_event.set()
                # block here so that the session will not be closed after exit scope
                # we could retrieve alive session through self.session
                await self.wait_for_shutdown_request()

    async def _server_lifespan_cycle(self):
        try:
            await self._connect_to_server(self._transport_context_factory(self.server_config))
        except* HTTPStatusError as e:
            if isinstance(self.server_config, RemoteServerConfig):
                logger.warning(f"Failed to connect to server {self.server_config.name} with streamablehttp, try sse")
                await self._connect_to_server(_sse_transport_context(self.server_config))
            else:
                raise e
        except* Exception as e:
            logger.error(f"Failed to connect to server {self.server_config.name}: {e}")
            self._initialized_event.set()
            self._shutdown_event.set()
