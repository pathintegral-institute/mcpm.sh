import asyncio
import logging
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

from mcpm.monitor.event import monitor
from mcpm.router.router import MCPRouter

from .middleware import SessionMiddleware
from .session import SessionManager
from .transport import SseTransport

logger = logging.getLogger("mcpm.router")

session_manager = SessionManager()
transport = SseTransport(endpoint="/messages/", session_manager=session_manager)

router = MCPRouter(reload_server=False)

class NoOpsResponse(Response):
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # To comply with Starlette's ASGI application design, this method must return a response.
        # Since no further client interaction is needed after server shutdown, we provide a no-operation response
        # that allows the application to exit gracefully when cancelled by Uvicorn.
        # No content is sent back to the client as EventSourceResponse has already returned a 200 status code.
        pass


async def handle_sse(request: Request):
    try:
        async with transport.connect_sse(request.scope, request.receive, request._send) as (read, write):
            await router.aggregated_server.run(read, write, router.aggregated_server.initialization_options) # type: ignore
    except asyncio.CancelledError:
        return NoOpsResponse()


@asynccontextmanager
async def lifespan(app):
    logger.info("Starting MCPRouter...")
    await router.initialize_router()
    await monitor.initialize_storage()

    yield

    logger.info("Shutting down MCPRouter...")
    await router.shutdown()
    await monitor.close()

app = Starlette(
    debug=True,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=transport.handle_post_message)
    ],
    middleware=[Middleware(SessionMiddleware, session_manager=session_manager)],
    lifespan=lifespan
)
