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
]

# All command modules


from . import client, inspector, list, profile, router, search
from .server_operations import add, custom, pop, remove, stash, transfer
