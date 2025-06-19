"""Tiny stub of the *deprecated* package.

The real package provides a decorator emitting run-time warnings when a
function is called.  For the purposes of the unit tests a *no-op* decorator is
perfectly adequate.
"""

from __future__ import annotations

from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable[..., object])


def deprecated(reason: str | None = None):  # noqa: D401 – decorator factory stub
    def decorator(func: F) -> F:  # noqa: D401 – inner decorator
        return func  # type: ignore[return-value]

    return decorator


__all__ = ["deprecated"]

