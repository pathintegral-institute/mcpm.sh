"""
Monitoring functionality for MCPM
"""

from typing import Optional

# Re-export base interfaces
from .base import AccessEventType, AccessMonitor

# session_tracker utilities removed - now handled by MCPMUnifiedTrackingMiddleware
# Re-export implementations
from .sqlite import SQLiteAccessMonitor


# Convenience function
async def get_monitor(db_path: Optional[str] = None) -> AccessMonitor:
    """
    Get a configured access monitor instance

    Args:
        db_path: Optional custom path to the database file. If None, uses the default
                config directory from ConfigManager.

    Returns:
        Configured AccessMonitor instance
    """
    monitor = SQLiteAccessMonitor(db_path)
    await monitor.initialize_storage()
    return monitor


# Exports
__all__ = [
    "AccessEventType",
    "AccessMonitor",
    "SQLiteAccessMonitor",
    "get_monitor",
]
