import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.routing import Mount, Route

from mcpm.router.router import MCPRouter
from mcpm.router.transport import RouterSseTransport
from mcpm.utils.platform import get_log_directory

LOG_DIR = get_log_directory("mcpm")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "router.log"
CORS_ENABLED = os.environ.get("MCPM_ROUTER_CORS")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger("mcpm.router.daemon")

router = MCPRouter(reload_server=True)
sse = RouterSseTransport("/messages/")


async def handle_sse(request: Request) -> None:
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


@asynccontextmanager
async def lifespan(app):
    logger.info("Starting MCPRouter...")
    await router.initialize_router()

    yield

    logger.info("Shutting down MCPRouter...")
    await router.shutdown()


middlewares = []
if CORS_ENABLED:
    allow_origins = os.environ.get("MCPM_ROUTER_CORS", "").split(",")
    middlewares.append(
        Middleware(CORSMiddleware, allow_origins=allow_origins, allow_methods=["*"], allow_headers=["*"])
    )

app = Starlette(
    debug=False,
    middleware=middlewares,
    routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ],
    lifespan=lifespan,
)
