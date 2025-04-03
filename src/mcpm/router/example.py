"""
Example script demonstrating how to use the MCPRouter to aggregate multiple MCP servers.
"""

import argparse
import asyncio
import json
import logging
import os
import pathlib
import traceback
from typing import List

from pydantic import BaseModel

from .connection_types import ConnectionDetails, ConnectionType
from .router import MCPRouter

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ServersConfig(BaseModel):
    """Configuration model for MCP servers."""

    servers: list[ConnectionDetails]


async def main(servers_config: ServersConfig, host: str, port: int, allow_origins: List[str] = None):
    """
    Main function to run the router example.

    Args:
        servers_config: Configuration containing list of server connection details
        host: Host to bind the SSE server to
        port: Port to bind the SSE server to
        allow_origins: List of allowed origins for CORS
    """
    router = MCPRouter()

    logger.info(f"Starting MCPRouter - will expose SSE server on http://{host}:{port}")

    # Add each server to the router
    for connection in servers_config.servers:
        try:
            logger.info(f"Adding server {connection.id} ({connection.type})")
            await router.add_server(connection.id, connection)
            logger.info(f"Successfully added server {connection.id}")
        except Exception as e:
            traceback.print_exc()
            logger.error(f"Failed to add server {connection.id}: {e}")

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
    parser.add_argument("--config", type=str, help="Path to servers configuration JSON file")
    parser.add_argument("--host", type=str, default="localhost", help="Host to bind the SSE server to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind the SSE server to")
    parser.add_argument("--cors", type=str, help="Comma-separated list of allowed origins for CORS")

    args = parser.parse_args()

    # Parse CORS origins
    allow_origins = None
    if args.cors:
        allow_origins = [origin.strip() for origin in args.cors.split(",")]

    # Get the directory of this script
    script_dir = pathlib.Path(__file__).parent.absolute()

    # Set default config file path
    if args.config is None:
        args.config = os.path.join(script_dir, "servers.json")

    # Load and parse servers configuration
    if os.path.exists(args.config):
        with open(args.config, "r") as f:
            raw_config = json.load(f)
            # Parse the entire config into ServersConfig
            servers_config = ServersConfig.model_validate({"servers": raw_config})
            logger.info(f"Loaded configuration from {args.config}")
    else:
        logger.warning(f"Config file not found: {args.config}")
        logger.info("Using example configuration")
        servers_config = ServersConfig(
            servers=[
                ConnectionDetails(
                    id="example1",
                    type=ConnectionType.STDIO,
                    command="python",
                    args=["-m", "mcp.examples.simple_server"],
                )
            ]
        )

    asyncio.run(main(servers_config, args.host, args.port, allow_origins))
