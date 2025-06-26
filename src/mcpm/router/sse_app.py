import asyncio
import logging
import os
import re
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

from mcpm.core.utils.log_manager import get_log_directory
from mcpm.monitor.base import AccessEventType
from mcpm.monitor.event import monitor
from mcpm.router.router import MCPRouter
from mcpm.router.transport import RouterSseTransport
from mcpm.utils.config import ConfigManager

LOG_DIR = get_log_directory("mcpm")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "router.log"
CORS_ENABLED = os.environ.get("MCPM_ROUTER_CORS")

logging.basicConfig(
    level=logging.INFO if not os.environ.get("MCPM_DEBUG") else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger("mcpm.router.daemon")

config = ConfigManager().get_router_config()
api_key = config.get("api_key")
auth_enabled = config.get("auth_enabled", False)

router = MCPRouter(reload_server=True)
sse = RouterSseTransport("/messages/", api_key=api_key if auth_enabled else None)


class NoOpsResponse(Response):
    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # To comply with Starlette's ASGI application design, this method must return a response.
        # Since no further client interaction is needed after server shutdown, we provide a no-operation response
        # that allows the application to exit gracefully when cancelled by Uvicorn.
        # No content is sent back to the client as EventSourceResponse has already returned a 200 status code.
        pass


async def handle_sse(request: Request):
    try:
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await router.aggregated_server.run(
                read_stream,
                write_stream,
                router.aggregated_server.initialization_options,  # type: ignore
            )
    except asyncio.CancelledError:
        return NoOpsResponse()


async def handle_query_events(request: Request) -> Response:
    """
    Handle query events request.
    """
    try:
        offset = request.query_params.get("offset")
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))
        event_type_str = request.query_params.get("event_type", None)

        if offset is None:
            return JSONResponse(
                {
                    "error": "Missing required parameter",
                    "detail": "The 'offset' parameter is required. Example: '24h' for past 24 hours.",
                },
                status_code=400,
            )

        offset_pattern = r"^(\d+)([hdwm])$"
        match = re.match(offset_pattern, offset.lower())
        if not match:
            valid_units = {"h": "hours", "d": "days", "w": "weeks", "m": "months"}
            return JSONResponse(
                {
                    "error": "Invalid offset format",
                    "detail": f"The offset must be in the format of a number followed by a valid time unit. "
                    f"Valid units are: {', '.join([f'{k} ({v})' for k, v in valid_units.items()])}. "
                    f"Examples: '24h', '7d', '2w', '1m'.",
                },
                status_code=400,
            )

        if page < 1:
            page = 1

        event_type = None
        if event_type_str:
            try:
                event_type = AccessEventType[event_type_str.upper()].name
            except (KeyError, ValueError):
                logger.warning(f"Invalid event_type: {event_type_str}")
                return JSONResponse(
                    {
                        "error": "Invalid event type",
                        "detail": f"'{event_type_str}' is not a valid event type. Valid types are: {', '.join([e.name for e in AccessEventType])}",
                    },
                    status_code=400,
                )

        response = await monitor.query_events(offset, page, limit, event_type)
        return JSONResponse(response.model_dump(), status_code=200)
    except Exception as e:
        logger.error(f"Error handling query events request: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@asynccontextmanager
async def lifespan(app):
    logger.info("Starting MCPRouter...")
    await router.initialize_router()
    await monitor.initialize_storage()

    yield

    logger.info("Shutting down MCPRouter...")
    await router.shutdown()
    await monitor.close()


middlewares = []
if CORS_ENABLED:
    allow_origins = os.environ.get("MCPM_ROUTER_CORS", "").split(",")
    middlewares.append(
        Middleware(CORSMiddleware, allow_origins=allow_origins, allow_methods=["*"], allow_headers=["*"])
    )

app = Starlette(
    debug=os.environ.get("MCPM_DEBUG") == "true",
    middleware=middlewares,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/events", endpoint=handle_query_events, methods=["GET"]),
        Mount("/messages/", app=sse.handle_post_message),
    ],
    lifespan=lifespan,
)
