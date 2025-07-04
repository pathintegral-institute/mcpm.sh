"""
MCPM commands package
"""

__all__ = [
    "add",
    "client",
    "config",
    "doctor",
    "info",
    "inspect",
    "inspector",
    "list",
    "profile",
    "remove",
    "run",
    "search",
    "usage",
]

# All command modules


from . import (
    client,
    config,
    doctor,
    info,
    inspect,
    inspector,
    list,
    profile,
    run,
    search,
    usage,
)
from .target_operations import add, remove
