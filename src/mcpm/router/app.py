import logging
import os
import asyncio
import re
from contextlib import asynccontextmanager

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from mcpm.monitor.event import monitor
from mcpm.monitor.base import AccessEventType
from mcpm.router.router import MCPRouter
from mcpm.router.router_config import RouterConfig
from mcpm.router.transport import RouterSseTransport
from mcpm.utils.config import ConfigManager
from mcpm.utils.platform import get_log_directory

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

router_instance = MCPRouter(reload_server=True, router_config=RouterConfig(api_key=api_key, auth_enabled=auth_enabled))
sse_transport = RouterSseTransport("/messages/", api_key=api_key if auth_enabled else None)

class NoOpsResponse(Response):
    def __init__(self):
        super().__init__(content=b"", status_code=204)

    async def __call__(self, scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.render_headers(),
            }
        )
        await send({"type": "http.response.body", "body": b"", "more_body": False})

async def handle_sse(request: Request):
    try:
        async with sse_transport.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await router_instance.aggregated_server.run(
                read_stream,
                write_stream,
                router_instance.aggregated_server.initialization_options,
            )
            while not await request.is_disconnected():
                await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in app.py handle_sse: {e}", exc_info=True)
    finally:
        return NoOpsResponse()

async def handle_query_events(request: Request) -> Response:
    try:
        offset = request.query_params.get("offset")
        page = int(request.query_params.get("page", 1))
        limit = int(request.query_params.get("limit", 10))
        event_type_str = request.query_params.get("event_type", None)

        if offset is None:
            return JSONResponse(
                {"error": "Missing required parameter", "detail": "The 'offset' parameter is required."},
                status_code=400,
            )
        
        offset_pattern = r"^(\d+)([hdwm])$"
        match = re.match(offset_pattern, offset.lower())
        if not match:
            return JSONResponse(
                {"error": "Invalid offset format", "detail": "Offset must be e.g., '24h', '7d', '2w', '1m'."},
                status_code=400,
            )

        if page < 1:
            page = 1
        event_type = None
        if event_type_str:
            try:
                event_type = AccessEventType[event_type_str.upper()].name
            except (KeyError, ValueError):
                return JSONResponse(
                    {"error": "Invalid event type", "detail": f"Valid types: {', '.join([e.name for e in AccessEventType])}"},
                    status_code=400,
                )
        
        if monitor:
             response_data = await monitor.query_events(offset, page, limit, event_type)
             return JSONResponse(response_data.model_dump(), status_code=200)
        else:
            logger.warning("monitor object not available for /events route")
            return JSONResponse({"error": "Monitoring not available"}, status_code=503)

    except Exception as e:
        logger.error(f"Error handling query events request: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)

@asynccontextmanager
async def lifespan(app_starlette: Starlette):
    logger.info("Starting MCPRouter (via app.py)...")
    await router_instance.initialize_router()
    if monitor:
        await monitor.initialize_storage()
    yield
    logger.info("Shutting down MCPRouter (via app.py)...")
    await router_instance.shutdown()
    if monitor:
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
        Mount("/messages/", app=sse_transport.handle_post_message),
    ],
    lifespan=lifespan,
)
