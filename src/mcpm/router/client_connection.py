import asyncio
import logging
from typing import Optional, cast

from mcp import ClientSession, InitializeResult, StdioServerParameters, stdio_client
from mcp.client.sse import sse_client

from mcpm.schemas.server_config import ServerConfig, SSEServerConfig, STDIOServerConfig

logger = logging.getLogger(__name__)


def _stdio_transport_context(server_config: ServerConfig):
    server_config = cast(STDIOServerConfig, server_config)
    server_params = StdioServerParameters(command=server_config.command, args=server_config.args, env=server_config.env)
    return stdio_client(server_params)


def _sse_transport_context(server_config: ServerConfig):
    server_config = cast(SSEServerConfig, server_config)
    return sse_client(server_config.url, headers=server_config.headers)


class ServerConnection:
    def __init__(self, server_config: ServerConfig) -> None:
        self.session: Optional[ClientSession] = None
        self.session_initialized_response: Optional[InitializeResult] = None
        self._initialized = False
        self.server_config = server_config
        self._initialized_event = asyncio.Event()
        self._shutdown_event = asyncio.Event()

        self._transport_context_factory = (
            _stdio_transport_context if isinstance(server_config, STDIOServerConfig) else _sse_transport_context
        )

        self._server_task = asyncio.create_task(self._server_lifespan_cycle())

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

    async def _server_lifespan_cycle(self):
        try:
            async with self._transport_context_factory(self.server_config) as (read, write):
                async with ClientSession(read, write) as session:
                    self.session_initialized_response = await session.initialize()

                    self.session = session
                    self._initialized = True
                    self._initialized_event.set()
                    # block here so that the session will not be closed after exit scope
                    # we could retrieve alive session through self.session
                    await self.wait_for_shutdown_request()
        except Exception as e:
            logger.error(f"Failed to connect to server {self.server_config.name}: {e}")
            self._initialized_event.set()
            self._shutdown_event.set()
