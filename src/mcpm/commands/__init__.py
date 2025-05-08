"""
MCPM commands package
"""

__all__ = [
    "add",
    "client",
    "inspector",
    "list",
    "pop",
    "profile",
    "remove",
    "search",
    "stash",
    "transfer",
    "router",
    "custom",
    "target",
]

# All command modules


from . import client, inspector, list, profile, router, search, target
from .target_operations import add, custom, pop, remove, stash, transfer
