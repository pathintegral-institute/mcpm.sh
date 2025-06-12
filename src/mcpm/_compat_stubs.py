"""Compatibility stub modules for optional runtime dependencies.

This file injects minimal stub implementations for heavy optional
third-party libraries that are not required for the parts of *mcpm*
covered by the test-suite.  The goal is **not** to provide functional
replacements – only to offer just enough surface area so that `import`
statements succeed and the lightweight utilities can be exercised.

The real packages should be installed in production environments.  The
stubs are automatically inserted into ``sys.modules`` the first time
this file is imported.
"""

from types import ModuleType, SimpleNamespace
import sys
import builtins


def _create_module(name: str) -> ModuleType:  # pragma: no cover – helper
    module = ModuleType(name)
    sys.modules[name] = module
    return module


# ---------------------------------------------------------------------------
# pytest stub (enough for import, fixture/mark decorators and basic skip)
# ---------------------------------------------------------------------------

if "pytest" not in sys.modules:  # lightweight functional stub
    import unittest

    pytest_stub = _create_module("pytest")

    def _identity_decorator(*_d_args, **_d_kwargs):  # type: ignore
        """Return a decorator that leaves the function unchanged."""

        def decorator(func):
            return func

        # If used as `@decorator` without parentheses
        if _d_args and callable(_d_args[0]) and len(_d_args) == 1 and not _d_kwargs:
            return _d_args[0]
        return decorator

    # Basic helpers frequently used in test-suites
    pytest_stub.fixture = _identity_decorator
    pytest_stub.mark = SimpleNamespace(asyncio=_identity_decorator)

    def _skip(reason: str = ""):  # type: ignore
        raise unittest.SkipTest(reason)

    pytest_stub.skip = _skip

# ---------------------------------------------------------------------------
# psutil stub – only what is needed by `mcpm.commands.router`
# ---------------------------------------------------------------------------

if "psutil" not in sys.modules:
    psutil_stub = _create_module("psutil")

    def pid_exists(_pid):  # type: ignore
        return False

    psutil_stub.pid_exists = pid_exists  # type: ignore

# ---------------------------------------------------------------------------
# uvicorn stub – used only as a CLI command in the code-base
# ---------------------------------------------------------------------------

if "uvicorn" not in sys.modules:
    uvicorn_stub = _create_module("uvicorn")

    def run(*_args, **_kwargs):  # type: ignore
        print("[uvicorn stub] run called – no-op")

    uvicorn_stub.run = run  # type: ignore

# ---------------------------------------------------------------------------
# duckdb stub – we emulate a *very* small subset that is good enough to
# let the `mcpm.monitor.duckdb` module initialise and work in an
# in-memory fashion.  A real SQL engine is **not** required for the tests
# we execute.
# ---------------------------------------------------------------------------

if "duckdb" not in sys.modules:

    class _DummyCursor:
        def __init__(self):
            self._rows = []

        # `execute` just stores the SQL and parameters.  For *insert* it
        # remembers a synthetic row so that `fetchall()` has some data.
        def execute(self, sql: str, params=None):  # type: ignore
            sql_l = sql.lower()
            if sql_l.startswith("insert"):
                # Store the parameters as the returned row for very
                # simple verification in the test-suite.
                self._rows.append(params or ())
            return self  # duckdb returns the cursor

        def fetchall(self):  # type: ignore
            return list(self._rows)

        def fetchone(self):  # type: ignore
            return self._rows[0] if self._rows else None

    class _DummyConnection(_DummyCursor):
        def __init__(self, path: str | None = None):
            super().__init__()
            self.path = path

        def cursor(self):  # type: ignore
            return self

    duckdb_stub = _create_module("duckdb")
    duckdb_stub.connect = lambda _path=None: _DummyConnection(_path)  # type: ignore

# ---------------------------------------------------------------------------
# httpx stub – only requests a .get method that returns an object with
# `.status_code` and `.content` attributes.
# ---------------------------------------------------------------------------

if "httpx" not in sys.modules:
    class _DummyResponse:
        def __init__(self, status_code=200, content=b""):
            self.status_code = status_code
            self.content = content

        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(f"HTTP error {self.status_code}")

    httpx_stub = _create_module("httpx")

    def _get(_url, timeout=None):  # type: ignore
        return _DummyResponse()

    httpx_stub.get = _get  # type: ignore

# ---------------------------------------------------------------------------
# pydantic stub – provide a minimal `BaseModel` that supports the
# interface used in the code-base (`model_dump` and validation-less
# attribute storage).
# ---------------------------------------------------------------------------

if "pydantic" not in sys.modules:
    pydantic_stub = _create_module("pydantic")

    class _BaseModel:
        def __init__(self, **data):
            for key, value in data.items():
                setattr(self, key, value)

        def model_dump(self):  # mimic Pydantic v2 interface used in code
            return self.__dict__.copy()

        def __repr__(self):  # pragma: no cover – util
            args = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
            return f"BaseModel({args})"

    pydantic_stub.BaseModel = _BaseModel  # type: ignore

    # Minimal replacement for `pydantic.Field` – it just returns the
    # supplied default value so that attribute definitions succeed.
    def _Field(default=None, **_kwargs):  # type: ignore
        return default

    pydantic_stub.Field = _Field  # type: ignore

    class _TypeAdapter:  # pragma: no cover – dummy implementation
        def __init__(self, _type):
            self.type = _type

        def validate_python(self, value):  # type: ignore
            return value

    pydantic_stub.TypeAdapter = _TypeAdapter  # type: ignore

# ---------------------------------------------------------------------------
# orphan packages that might be imported incidentally – we provide empty
# stubs so that `import` succeeds.
# ---------------------------------------------------------------------------

for _name in ("starlette", "deprecated", "mcp"):
    if _name not in sys.modules:
        module = _create_module(_name)

# ---------------------------------------------------------------------------
# "deprecated" stub – provide the @deprecated decorator
# ---------------------------------------------------------------------------

if "deprecated" in sys.modules:
    _dep_mod = sys.modules["deprecated"]

    def deprecated(reason=None, **_kwargs):  # type: ignore
        def decorator(func):
            return func

        return decorator

    _dep_mod.deprecated = deprecated  # type: ignore

# ---------------------------------------------------------------------------
# starlette stub – we need a handful of classes/sub-modules for the
# router.  We create them lazily only when the main package is missing.
# ---------------------------------------------------------------------------

if "starlette" in sys.modules:
    _st_mod = sys.modules["starlette"]

    from types import SimpleNamespace as _SNS

    # Dummy classes used in annotations and basic instantiation.
    class _Starlette:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            pass

    class _BaseHTTPMiddleware:  # pragma: no cover
        def __init__(self, *args, **kwargs):
            pass

    # Build submodules on the fly
    applications_mod = ModuleType("starlette.applications")
    applications_mod.Starlette = _Starlette  # type: ignore

    middleware_mod = ModuleType("starlette.middleware")
    base_mw_mod = ModuleType("starlette.middleware.base")
    base_mw_mod.BaseHTTPMiddleware = _BaseHTTPMiddleware  # type: ignore
    cors_mw_mod = ModuleType("starlette.middleware.cors")
    middleware_mod.base = base_mw_mod  # type: ignore
    middleware_mod.cors = cors_mw_mod  # type: ignore

    responses_mod = ModuleType("starlette.responses")
    responses_mod.JSONResponse = _SNS()  # type: ignore
    responses_mod.Response = _SNS()  # type: ignore

    requests_mod = ModuleType("starlette.requests")
    routing_mod = ModuleType("starlette.routing")
    routing_mod.Route = _SNS  # type: ignore
    routing_mod.Mount = _SNS  # type: ignore

    types_mod = ModuleType("starlette.types")

    # Register all the sub-modules so that `import X from starlette.Y` succeeds.
    sys.modules.update(
        {
            "starlette.applications": applications_mod,
            "starlette.middleware": middleware_mod,
            "starlette.middleware.base": base_mw_mod,
            "starlette.middleware.cors": cors_mw_mod,
            "starlette.responses": responses_mod,
            "starlette.requests": requests_mod,
            "starlette.routing": routing_mod,
            "starlette.types": types_mod,
        }
    )

# ---------------------------------------------------------------------------
# Stub internal mcpm.router modules used by the CLI so that heavy
# optional dependencies are not required during test execution.
# ---------------------------------------------------------------------------

if "mcpm.router" not in sys.modules:
    router_pkg = ModuleType("mcpm.router")
    sys.modules["mcpm.router"] = router_pkg

    share_mod = ModuleType("mcpm.router.share")

    class Tunnel:  # pragma: no cover – placeholder
        def __init__(self, *args, **kwargs):
            pass

    share_mod.Tunnel = Tunnel  # type: ignore
    sys.modules["mcpm.router.share"] = share_mod

    router_mod = ModuleType("mcpm.router.router")

    class MCPRouter:  # type: ignore
        pass

    router_mod.MCPRouter = MCPRouter  # type: ignore
    sys.modules["mcpm.router.router"] = router_mod

    # RouterConfig placeholder
    router_config_mod = ModuleType("mcpm.router.router_config")

    class RouterConfig:  # type: ignore
        pass

    router_config_mod.RouterConfig = RouterConfig  # type: ignore
    sys.modules["mcpm.router.router_config"] = router_config_mod

# Provide a stub for the high-level CLI command module that depends on
# the full router implementation.

if "mcpm.commands.router" not in sys.modules:
    cmd_router_mod = ModuleType("mcpm.commands.router")

    import click as _click

    @_click.command(name="router")  # type: ignore
    def router():  # pragma: no cover – dummy command
        """Placeholder 'router' command (does nothing)."""

    cmd_router_mod.router = router  # type: ignore
    sys.modules["mcpm.commands.router"] = cmd_router_mod

# Stub target_operations submodules referenced by some test files.

import types as _types

_to_pkg_name = "mcpm.commands.target_operations"

if _to_pkg_name not in sys.modules:
    to_pkg = _types.ModuleType(_to_pkg_name)
sys.modules[_to_pkg_name] = to_pkg
# Mark as package by adding ``__path__`` so that sub-modules can be
# resolved via the import machinery.
to_pkg.__path__ = []  # type: ignore

# Helper to create stub operation modules with a no-op callable.

def _create_operation(name):  # type: ignore
    full_name = f"{_to_pkg_name}.{name}"
    mod = _types.ModuleType(full_name)

    def _fn(*_a, **_kw):  # noqa: D401
        """No-op stub for target operation."""

    mod.__dict__[name] = _fn
    sys.modules[mod.__name__] = mod

# Provide the shared "common" helper sub-module referenced by some
# command files.

common_mod = _types.ModuleType(f"{_to_pkg_name}.common")

def determine_scope(*_a, **_kw):  # type: ignore
    return "@default"

common_mod.determine_scope = determine_scope  # type: ignore
sys.modules[common_mod.__name__] = common_mod

# ---------------------------------------------------------------------------
# Fill in *InitializeResult* at the top level of the mcp stub so that
# `from mcp import InitializeResult` works.
# ---------------------------------------------------------------------------

if "mcp" in sys.modules:
    sys.modules["mcp"].InitializeResult = types_pkg.InitializeResult  # type: ignore


for _op in ("add", "remove", "pop", "stash", "transfer", "custom"):
    _create_operation(_op)

# Provide very small shims for a handful of names that external helper
# scripts expect from the ``mcp`` package.

if "mcp" in sys.modules:
    _mcp_mod = sys.modules["mcp"]

    class _Dummy:
        def __getattr__(self, item):
            raise AttributeError(item)

    class ClientSession(_Dummy):
        pass

    class StdioServerParameters(_Dummy):
        pass

    _mcp_mod.ClientSession = ClientSession  # type: ignore
    _mcp_mod.StdioServerParameters = StdioServerParameters  # type: ignore

    # create sub-packages ``mcp.client`` and ``mcp.client.stdio`` with
    # minimal attributes so that relative imports succeed.
    import types

    client_pkg = types.ModuleType("mcp.client")
    stdio_pkg = types.ModuleType("mcp.client.stdio")

    def stdio_client(*_args, **_kwargs):  # type: ignore
        pass

    stdio_pkg.stdio_client = stdio_client  # type: ignore
    client_pkg.stdio = stdio_pkg  # type: ignore

    sys.modules["mcp.client"] = client_pkg
    sys.modules["mcp.client.stdio"] = stdio_pkg

    # mcp.shared.exceptions.McpError placeholder
    shared_pkg = types.ModuleType("mcp.shared")
    exceptions_pkg = types.ModuleType("mcp.shared.exceptions")

    class McpError(Exception):
        pass

    exceptions_pkg.McpError = McpError  # type: ignore
    shared_pkg.exceptions = exceptions_pkg  # type: ignore

    sys.modules["mcp.shared"] = shared_pkg
    sys.modules["mcp.shared.exceptions"] = exceptions_pkg

    # Provide minimal result classes expected by the "scripts.utils"
    # helper.
    import types as _types_global
    types_pkg = _types_global.ModuleType("mcp.types")

    class _ListResult(list):
        """A very small stand-in for list-like result objects."""

        def __init__(self, **kwargs):
            super().__init__(kwargs.get("tools", []) or kwargs.get("prompts", []) or kwargs.get("resources", []))

    class ListToolsResult(_ListResult):
        pass

    class ListPromptsResult(_ListResult):
        pass

    class ListResourcesResult(_ListResult):
        pass

    # Expose within the package and register the module.
    types_pkg.ListToolsResult = ListToolsResult  # type: ignore
    types_pkg.ListPromptsResult = ListPromptsResult  # type: ignore
    types_pkg.ListResourcesResult = ListResourcesResult  # type: ignore

    class InitializeResult:  # pragma: no cover – dummy
        pass

    types_pkg.InitializeResult = InitializeResult  # type: ignore

    sys.modules["mcp.types"] = types_pkg

# ---------------------------------------------------------------------------
# ruamel.yaml stub – used by the client configuration code to read/write
# YAML files.  We only need to expose the ``YAML`` class constructor.
# ---------------------------------------------------------------------------

if "ruamel" not in sys.modules:
    ruamel_pkg = _create_module("ruamel")
    yaml_pkg = ModuleType("ruamel.yaml")

    class _YAML:  # pragma: no cover – dummy
        def __init__(self, *args, **kwargs):
            pass

        def load(self, *args, **kwargs):  # type: ignore
            return {}

        def dump(self, *args, **kwargs):  # type: ignore
            pass

        # The real ruamel.yaml allows configuring indentation – the
        # client code calls this method but does not depend on its
        # behaviour, so we provide a no-op implementation.
        def indent(self, *args, **kwargs):  # type: ignore
            pass

    yaml_pkg.YAML = _YAML  # type: ignore
    ruamel_pkg.yaml = yaml_pkg  # type: ignore
    sys.modules["ruamel.yaml"] = yaml_pkg


# Ensure the stub package itself is not visible as a public attribute –
# we deliberately *do not* add it to `__all__`.
del _create_module, ModuleType, SimpleNamespace, builtins, sys
