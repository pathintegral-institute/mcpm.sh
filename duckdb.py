"""Tiny stub for the *duckdb* package required by the access monitor module."""

from __future__ import annotations


class DuckDBPyConnection:  # noqa: D101 – placeholder connection class
    def __init__(self, *args, **kwargs):  # noqa: D401 – no-op
        pass

    # Provide very light-weight cursor like interface used by the monitor.
    def execute(self, *args, **kwargs):  # noqa: D401 – chainable
        return self

    def fetchall(self):  # noqa: D401 – return empty list
        return []


# Convenience helper used in code-base: ``duckdb.connect``


def connect(*args, **kwargs):  # noqa: D401 – returns stub connection
    return DuckDBPyConnection()


__all__ = ["connect", "DuckDBPyConnection"]

