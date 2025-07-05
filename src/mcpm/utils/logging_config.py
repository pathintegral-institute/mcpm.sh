"""
Simple logging configuration using Rich, following FastMCP pattern.
"""

import logging
import os

from rich.console import Console
from rich.logging import RichHandler


def setup_logging() -> None:
    """
    Configure basic logging to use Rich handler for beautiful output.

    This sets up the core logging infrastructure used by all MCPM commands:
    - Uses MCPM_DEBUG or MCPM_LOG_LEVEL environment variables
    - Configures root logger with RichHandler
    - Suppresses general third-party library noise

    For commands using FastMCP/MCP, call setup_dependency_logging() as well.
    """
    # Determine log level from environment
    debug_enabled = is_debug_enabled()
    log_level = os.getenv("MCPM_LOG_LEVEL", "DEBUG" if debug_enabled else "INFO")

    # Create Rich handler with timestamp and class information
    handler = RichHandler(
        console=Console(stderr=True),
        rich_tracebacks=True,
        show_time=True,  # Show timestamps
        show_path=False,  # Keep path clean
    )

    # Configure root logger with timestamp and class name format
    logging.basicConfig(
        level=log_level,
        format="%(name)s: %(message)s",  # Include class/module name
        handlers=[handler],
        force=True,  # Replace any existing handlers
    )

    # Apply basic library suppression for general third-party libraries
    _suppress_general_libraries(debug_enabled)


def _suppress_general_libraries(debug_enabled: bool) -> None:
    """Suppress general third-party library logging."""
    # Configure general third-party library logging levels
    # In debug mode, let them log at their normal levels
    # Otherwise, suppress to WARNING to reduce noise
    third_party_level = logging.DEBUG if debug_enabled else logging.WARNING

    logging.getLogger("httpx").setLevel(third_party_level)
    logging.getLogger("httpcore").setLevel(third_party_level)
    logging.getLogger("asyncio").setLevel(third_party_level)
    logging.getLogger("urllib3").setLevel(third_party_level)


def setup_dependency_logging() -> None:
    """Configure MCP/FastMCP dependency logging for run and share commands.

    This should be called in commands that use FastMCP or MCP libraries
    to suppress their verbose logging output.
    """
    debug_enabled = is_debug_enabled()

    # Configure MCP-related libraries
    for mcp_logger_name in ["mcp", "mcp.client", "mcp.server", "FastMCP", "FastMCP.server", "FastMCP.client"]:
        mcp_logger = logging.getLogger(mcp_logger_name)
        mcp_logger.handlers = []  # Remove any handlers they might add
        mcp_logger.propagate = True  # Use our root handler
        mcp_logger.setLevel(logging.INFO if debug_enabled else logging.WARNING)


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled via environment variables."""
    return os.getenv("MCPM_DEBUG", "").lower() in ("1", "true", "yes")


def get_uvicorn_log_level() -> str:
    """Get appropriate uvicorn log level based on debug settings."""
    return "info" if is_debug_enabled() else "warning"


def ensure_dependency_logging_suppressed() -> None:
    """Re-apply dependency logging suppression after FastMCP initialization.

    Call this after creating FastMCP proxies to ensure logging stays suppressed.
    """
    setup_dependency_logging()
