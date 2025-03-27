"""
MCPM commands package
"""

__all__ = [
    "add",
    "client",
    "edit",
    "inspector",
    "list",
    "remove",
    "search",
    "server",
    "toggle"
]

# All command modules
from . import add
from . import client
from . import edit
from . import inspector
from . import list
from . import remove
from . import search
from . import server
from . import toggle
