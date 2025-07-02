"""
MCPM commands package
"""

__all__ = [
    "add",
    "client", 
    "config",
    "doctor",
    "import_client",
    "info",
    "inspect", 
    "inspector",
    "list",
    "profile",
    "remove",
    "router",
    "run",
    "search",
    "usage",
]

# All command modules


from . import (
    client,
    config,
    doctor,
    import_client,
    info,
    inspect,
    inspector,
    list,
    profile,
    router,
    run,
    search,
    usage,
)
from .target_operations import add, remove
