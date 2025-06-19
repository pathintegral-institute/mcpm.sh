"""Rudimentary stub for the *starlette* package.

The router imports ``Starlette`` from ``starlette.applications`` but the class
is never instantiated within the unit tests.  A simple placeholder is
sufficient.
"""

from __future__ import annotations

import sys
from types import ModuleType


class _StarletteStub:  # noqa: D101 – placeholder class
    def __init__(self, *args, **kwargs):  # noqa: D401 – no behaviour
        pass


# Create sub-module ``starlette.applications`` dynamically.
applications_module = ModuleType("starlette.applications")
applications_module.Starlette = _StarletteStub  # type: ignore[attr-defined]

# Register in *sys.modules* so that’import statements succeed.
sys.modules[applications_module.__name__] = applications_module

# ---------------------------------------------------------------------------
# Additional sub-modules referenced by *mcpm.router.router*.
# ---------------------------------------------------------------------------


def _make_module(name: str, **attrs):
    module = ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


# starlette.middleware & subpackages
_make_module(
    "starlette.middleware",
    Middleware=type("Middleware", (), {}),
)
_make_module(
    "starlette.middleware.base",
    BaseHTTPMiddleware=type("BaseHTTPMiddleware", (), {}),
)
_make_module(
    "starlette.middleware.cors",
    CORSMiddleware=type("CORSMiddleware", (), {}),
)

# starlette.requests
_make_module(
    "starlette.requests",
    Request=type("Request", (), {}),
)

# starlette.responses
_make_module(
    "starlette.responses",
    JSONResponse=type("JSONResponse", (), {}),
    Response=type("Response", (), {}),
)

# starlette.routing
_make_module(
    "starlette.routing",
    Mount=type("Mount", (), {}),
    Route=type("Route", (), {}),
)

# starlette.types
_make_module(
    "starlette.types",
    Lifespan=type("Lifespan", (), {}),
    Receive=type("Receive", (), {}),
    Scope=type("Scope", (), {}),
    Send=type("Send", (), {}),
)

# Clean public namespace.
__all__: list[str] = []
