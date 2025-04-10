"""
Example script demonstrating how to use the MCPRouter to aggregate multiple MCP servers.
"""

import argparse
import asyncio
import logging
from typing import List

from .router import MCPRouter

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def main(host: str, port: int, allow_origins: List[str] = None):
    """
    Main function to run the router example.

    Args:
        host: Host to bind the SSE server to
        port: Port to bind the SSE server to
        allow_origins: List of allowed origins for CORS
    """
    router = MCPRouter(reload_server=True)

    logger.info(f"Starting MCPRouter - will expose SSE server on http://{host}:{port}")

    # Start the SSE server
    try:
        logger.info(f"Starting SSE server on http://{host}:{port}")
        if allow_origins:
            logger.info(f"CORS enabled for origins: {allow_origins}")
        await router.start_sse_server(host, port, allow_origins)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error starting SSE server: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Router Example")
    parser.add_argument("--host", type=str, default="localhost", help="Host to bind the SSE server to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind the SSE server to")
    parser.add_argument("--cors", type=str, help="Comma-separated list of allowed origins for CORS")

    args = parser.parse_args()

    # Parse CORS origins
    allow_origins = None
    if args.cors:
        allow_origins = [origin.strip() for origin in args.cors.split(",")]

    asyncio.run(main(args.host, args.port, allow_origins))
