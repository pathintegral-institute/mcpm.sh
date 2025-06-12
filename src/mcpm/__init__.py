"""
MCPM - Model Context Protocol Manager
"""

# Load lightweight stub replacements for optional third-party
# dependencies *before* the rest of the public package is imported.  The
# stubs live in ``mcpm._compat_stubs`` and make sure that `import`ing
# *mcpm* does not fail in minimal environments (for example, the CI
# sandbox used for running the test-suite).

from importlib import import_module as _import_module  # noqa: E402

# Importing the module installs the stubs into ``sys.modules``.
_import_module("mcpm._compat_stubs")

# Clean up the helper reference to avoid leaking a private name into the
# public namespace.
del _import_module

# Import version from internal module
# Lazy-import heavy optional dependencies so that importing the
# lightweight utility sub-modules (e.g. ``mcpm.utils``) continues to
# work even when the optional runtime requirements such as ``uvicorn``
# or ``starlette`` are not available in the execution environment.
#
# The router functionality is only needed when users explicitly work
# with the router component. Importing it unconditionally would raise
# ``ImportError`` in environments where these heavy dependencies are
# absent, which in turn prevents *any* use of the package – including
# its pure-Python utilities – and also breaks unit-test discovery in
# constrained CI sandboxes.

# We therefore attempt to import the router related symbols, but fall
# back to ``None`` when any of the optional dependencies is missing.
# Consumers that rely on the router should check for ``None`` and act
# accordingly.

# Importing the router (and its heavy dependencies such as ``starlette``
# or ``uvicorn``) is entirely optional for most use-cases and noticeably
# increases the import time.  Moreover, these third-party packages might
# be absent in minimal or sandboxed environments (for instance, during
# execution of the test-suite in CI).
#
# To keep ``mcpm`` importable even when the optional dependencies are not
# available we perform the router import lazily: the first attempt happens
# only when either ``MCPRouter`` or ``RouterConfig`` is explicitly accessed
# via attribute look-up.  This is implemented through ``__getattr__`` which
# is supported starting with Python 3.7 (PEP 562).

from types import ModuleType
from importlib import import_module
from typing import Any


def __getattr__(name: str) -> Any:  # pragma: no cover – only executed on demand
    """Lazily import optional heavy sub-modules.

    This mechanism is transparent to the user: the first attribute access
    triggers the real import, subsequent accesses use the cached symbol
    directly.  If the import fails because the optional runtime
    dependencies are missing we raise ``AttributeError`` which matches the
    standard Python behaviour for missing attributes.
    """

    if name in {"MCPRouter", "RouterConfig"}:
        try:
            router_module = import_module("mcpm.router.router")
            config_module = import_module("mcpm.router.router_config")
            globals()["MCPRouter"] = getattr(router_module, "MCPRouter")
            globals()["RouterConfig"] = getattr(config_module, "RouterConfig")
            __all__.extend(["MCPRouter", "RouterConfig"])
            return globals()[name]
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise AttributeError(
                f"Optional dependency missing while importing '{name}': {exc.name}"
            ) from None
    raise AttributeError(f"module 'mcpm' has no attribute '{name}'")
from .version import __version__

# Define what symbols are exported from this package
# Only expose names that are actually available at runtime to avoid
# AttributeError when optional dependencies are missing.

# Public exports – ``MCPRouter`` and ``RouterConfig`` are added lazily
# when the optional dependencies are available (see ``__getattr__``)
# but we still need the names to exist at module initialisation time so
# that the attribute checks below do not raise ``NameError``.


# Placeholders for optional symbols (replaced on-demand in
# ``__getattr__`` when the real router can be imported successfully).

MCPRouter = None  # type: ignore
RouterConfig = None  # type: ignore

__all__ = ["__version__"]
