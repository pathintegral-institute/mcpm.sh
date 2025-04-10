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
, "router"]

# All command modules
from . import client, inspector, list, profile, search
from .server_operations import add, pop, remove, router, stash, transfer
