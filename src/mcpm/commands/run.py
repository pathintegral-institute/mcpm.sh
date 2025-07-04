"""Run command for MCPM - Execute servers directly over stdio or HTTP"""

import asyncio
import logging
import os
import subprocess
import sys

import click
from rich.console import Console

from mcpm.fastmcp_integration.proxy import create_mcpm_proxy
from mcpm.global_config import GlobalConfigManager
from mcpm.utils.config import DEFAULT_PORT
from mcpm.utils.logging_config import (
    ensure_dependency_logging_suppressed,
    get_uvicorn_log_level,
    setup_dependency_logging,
)

global_config_manager = GlobalConfigManager()
logger = logging.getLogger(__name__)
console = Console()


def find_installed_server(server_name):
    """Find an installed server by name in global configuration."""
    server_config = global_config_manager.get_server(server_name)
    if server_config:
        return server_config, "global"
    return None, None


def execute_server_command(server_config, server_name):
    """Execute a server command with proper environment setup."""
    if not server_config:
        logger.error(f"Invalid server configuration for '{server_name}'")
        sys.exit(1)

    # Get command and args from the server config
    command = server_config.command
    args = server_config.args or []

    if not command:
        logger.error(f"Invalid command format for server '{server_name}'")
        sys.exit(1)

    # Build the full command list
    full_command = [command] + args

    # Set up environment
    env = os.environ.copy()

    # Add any environment variables from server config
    if hasattr(server_config, "env") and server_config.env:
        for key, value in server_config.env.items():
            env[key] = str(value)

    # Set working directory if specified
    cwd = getattr(server_config, "cwd", None)
    if cwd:
        cwd = os.path.expanduser(cwd)

    try:
        # Record usage
        from mcpm.commands.usage import record_server_usage

        record_server_usage(server_name, "run")

        # Execute the command
        result = subprocess.run(full_command, env=env, cwd=cwd, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr)

        return result.returncode

    except FileNotFoundError:
        logger.error(f"Command not found: {full_command[0]}")
        logger.warning("Make sure the required runtime is installed")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server execution interrupted")
        logger.warning("\nServer execution interrupted")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error running server '{server_name}': {e}")
        sys.exit(1)


async def run_server_with_fastmcp(server_config, server_name, http_mode=False, port=None):
    """Run server using FastMCP proxy (stdio or HTTP)."""
    try:
        # Use default port if none specified
        if port is None:
            port = DEFAULT_PORT
        # Record usage
        from mcpm.commands.usage import record_server_usage

        record_server_usage(server_name, "run" + ("_http" if http_mode else ""))

        # Create FastMCP proxy for single server
        proxy = await create_mcpm_proxy(
            servers=[server_config],
            name=f"mcpm-run-{server_name}",
            stdio_mode=not http_mode,  # stdio_mode=False for HTTP
        )

        # Set up dependency logging for FastMCP/MCP libraries
        setup_dependency_logging()

        # Re-suppress library logging after FastMCP initialization
        ensure_dependency_logging_suppressed()

        if http_mode:
            # Try to find an available port if the requested one is taken
            actual_port = await find_available_port(port)
            if actual_port != port:
                logger.debug(f"Port {port} is busy, using port {actual_port} instead")

            # Display server information
            http_url = f"http://127.0.0.1:{actual_port}/mcp/"
            console.print(f"[bold green]Server '{server_name}' is now running at:[/]")
            console.print(f"[cyan]{http_url}[/]")
            console.print("[dim]Press Ctrl+C to stop the server[/]")

            logger.debug(f"Starting FastMCP proxy for server '{server_name}' on port {actual_port}")

            # Run FastMCP proxy in HTTP mode with uvicorn logging control
            await proxy.run_http_async(
                host="127.0.0.1", port=actual_port, uvicorn_config={"log_level": get_uvicorn_log_level()}
            )
        else:
            # Run FastMCP proxy in stdio mode (default)
            logger.info(f"Starting server '{server_name}' over stdio")
            await proxy.run_stdio_async()

        return 0

    except KeyboardInterrupt:
        logger.info("Server execution interrupted")
        if http_mode:
            logger.warning("\nServer execution interrupted")
        return 130
    except Exception as e:
        logger.error(f"Error running server '{server_name}': {e}")
        return 1


async def find_available_port(preferred_port, max_attempts=10):
    """Find an available port starting from preferred_port."""
    import socket

    for attempt in range(max_attempts):
        port_to_try = preferred_port + attempt

        # Check if port is available
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port_to_try))
                return port_to_try
        except OSError:
            continue  # Port is busy, try next one

    # If no port found, return the original (will likely fail but user will see the error)
    return preferred_port


@click.command()
@click.argument("server_name")
@click.option("--http", is_flag=True, help="Run server over HTTP instead of stdio")
@click.option("--port", type=int, default=DEFAULT_PORT, help=f"Port for HTTP mode (default: {DEFAULT_PORT})")
@click.help_option("-h", "--help")
def run(server_name, http, port):
    """Execute a server from global configuration over stdio or HTTP.

    Runs an installed MCP server from the global configuration. By default
    runs over stdio for client communication, but can run over HTTP with --http.

    Examples:
        mcpm run mcp-server-browse              # Run over stdio (default)
        mcpm run --http mcp-server-browse       # Run over HTTP on port 6276
        mcpm run --http --port 9000 filesystem # Run over HTTP on port 9000

    Note: stdio mode is typically used in MCP client configurations:
        {"command": ["mcpm", "run", "mcp-server-browse"]}
    """
    # Validate server name
    if not server_name or not server_name.strip():
        logger.error("Error: Server name cannot be empty")
        sys.exit(1)

    server_name = server_name.strip()

    # Find the server configuration
    server_config, location = find_installed_server(server_name)

    if not server_config:
        logger.error(f"Error: Server '{server_name}' not found")
        logger.warning("Available options:")
        logger.info("  • Run 'mcpm ls' to see installed servers")
        logger.info("  • Run 'mcpm search {name}' to find available servers")
        logger.info("  • Run 'mcpm install {name}' to install a server")
        sys.exit(1)

    # Debug logging is now handled by the Rich logging setup in CLI
    # Just log debug info - the level is controlled centrally
    logger.debug(f"Running server '{server_name}' from {location} configuration")
    logger.debug(f"Command: {server_config.command} {' '.join(server_config.args or [])}")
    logger.debug(f"Mode: {'HTTP' if http else 'stdio'}")
    if http:
        logger.debug(f"Port: {port}")

    # Choose execution method
    if http:
        # Use FastMCP proxy for HTTP mode
        exit_code = asyncio.run(run_server_with_fastmcp(server_config, server_name, http_mode=True, port=port))
    else:
        # Use direct execution for stdio mode (maintains backwards compatibility)
        exit_code = execute_server_command(server_config, server_name)

    sys.exit(exit_code)
