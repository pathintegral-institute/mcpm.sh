"""
Monitoring functionality for MCPM
"""

from typing import Optional

# Re-export base interfaces
from .base import AccessEventType, AccessMonitor

# Re-export implementations
from .duckdb import DuckDBAccessMonitor


# Convenience function to get a monitor instance
def get_monitor(db_path: Optional[str] = None) -> AccessMonitor:
    """
    Get a configured access monitor instance

    Args:
        db_path: Optional custom path to the database file

    Returns:
        Configured AccessMonitor instance
    """
    monitor = DuckDBAccessMonitor(db_path) if db_path else DuckDBAccessMonitor()
    monitor.initialize_storage()
    return monitor


# Exports
__all__ = [
    "AccessEventType",
    "AccessMonitor",
    "DuckDBAccessMonitor",
    "get_monitor",
]
