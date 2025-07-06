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
    "list",
    "migrate",
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
    list,
    migrate,
    profile,
    run,
    search,
    usage,
)
from .target_operations import add, remove
