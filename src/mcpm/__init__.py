"""
MCPM - Model Context Protocol Manager
"""

# Import version from internal module
# Import router module
from . import router
from .router.router import MCPRouter
from .router.router_config import RouterConfig
from .version import __version__

# Define what symbols are exported from this package
__all__ = ["__version__", "router", "MCPRouter", "RouterConfig"]
