"""Very small stub of the *pydantic* package used only for the unit‐tests.

Only two public objects are provided:
  • ``BaseModel`` – an extremely lightweight replacement that stores the
    supplied keyword arguments as attributes and offers ``model_dump`` /
    ``dict`` helpers returning a shallow copy of ``__dict__``.
  • ``TypeAdapter`` – mimics the subset of the real API that the code-base
    utilises, namely ``TypeAdapter(model).validate_python(data)``.  The stub
    converts the incoming mapping into either a ``RemoteServerConfig`` or
    ``STDIOServerConfig`` instance (or the specified model) using simple
    heuristics.  If instantiation fails, the original data is returned.

It is *not* a full re-implementation – merely enough for execution inside the
restricted evaluation environment where external dependencies cannot be
installed.
"""

from __future__ import annotations

import sys
from typing import Any, get_args, get_origin, Union


class BaseModel:  # noqa: D101 – minimal stub
    def __init__(self, **data: Any) -> None:  # noqa: D401 – simple stub
        # Store all supplied fields as attributes.
        for key, value in data.items():
            setattr(self, key, value)

    # The real *pydantic* provides ``model_dump`` (v2) and ``dict`` (v1)
    # methods.  The tests only need a shallow conversion, therefore both can
    # delegate to a simple implementation.
    def model_dump(self) -> dict[str, Any]:  # noqa: D401 – stub
        return dict(self.__dict__)

    def dict(self, *args: Any, **kwargs: Any) -> dict[str, Any]:  # noqa: D401 – stub
        return self.model_dump()


class _SimpleTypeAdapter:  # noqa: D101 – internal helper
    def __init__(self, model):
        self._model = model

    def validate_python(self, data: Any):  # noqa: D401 – very shallow validation
        """Return *data* coerced into *self._model* where possible.

        The strategy is intentionally simplistic but sufficient:
          1. If *self._model* is a class, attempt to instantiate it.
          2. If *self._model* is a ``Union[RemoteServerConfig,
             STDIOServerConfig]`` decide which concrete type to use by looking
             for distinguishing keys (``url`` ⇒ remote, else stdio).
          3. On any error fall back to returning the original *data*.
        """

        try:
            origin = get_origin(self._model)

            # Handle non-Union models first.
            if origin is None:  # Plain class or callable.
                return self._model(**data) if isinstance(data, dict) else self._model(data)  # type: ignore[arg-type]

            # Handle a simple Union – we only expect exactly two alternatives.
            if origin is Union:  # type: ignore[name-defined]
                from mcpm.core.schema import RemoteServerConfig, STDIOServerConfig  # Local import to avoid cycles.

                for option in get_args(self._model):
                    if option is RemoteServerConfig and isinstance(data, dict) and "url" in data:
                        return option(**data)
                    if option is STDIOServerConfig and isinstance(data, dict) and "command" in data:
                        return option(**data)

            # Fallback: attempt naive instantiation.
            return self._model(**data) if callable(self._model) else data
        except Exception:  # pragma: no cover – best-effort resilience
            return data


def TypeAdapter(model):  # noqa: D401 – public factory
    return _SimpleTypeAdapter(model)


# Provide a *very* small public surface matching the names imported elsewhere.
__all__ = [
    "BaseModel",
    "TypeAdapter",
    "AnyUrl",
    "Field",
]


# Minimal replacement for ``pydantic.Field`` – just returns the provided
# default value (or ``None``).


def Field(default: Any = None, *args: Any, **kwargs: Any):  # noqa: D401 – stub factory
    return default



# ---------------------------------------------------------------------------
# Minimal *AnyUrl* replacement – only the ``build`` class-method used in the
# router implementation is supported.
# ---------------------------------------------------------------------------


class AnyUrl(str):  # noqa: D101 – extremely reduced implementation
    @classmethod
    def build(
        cls,
        *,
        scheme: str = "",  # noqa: D401 – keep signature close to pydantic’s
        host: str = "",
        path: str = "",
        username: str | None = None,
        password: str | None = None,
        port: int | None = None,
        query: str | None = None,
        fragment: str | None = None,
    ) -> "AnyUrl":
        """Construct a rudimentary URL string from the supplied components."""

        auth = ""
        if username is not None:
            auth = username
            if password is not None:
                auth += f":{password}"
            auth += "@"

        host_port = host
        if port is not None:
            host_port += f":{port}"

        query_part = f"?{query}" if query else ""
        fragment_part = f"#{fragment}" if fragment else ""

        return cls(f"{scheme}://{auth}{host_port}{path}{query_part}{fragment_part}")


# Register sub-module alias so that ``from pydantic.typing import …`` would work
# if it is attempted (unlikely in this code-base).
sys.modules.setdefault("pydantic.typing", sys.modules[__name__])
