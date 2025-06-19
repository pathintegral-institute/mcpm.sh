"""Very small stub of the *uvicorn* package so that the code-base can be
imported inside environments where the real package is unavailable.

Only the attributes accessed by *mcpm* are provided.
"""


def run(*args, **kwargs):  # noqa: D401 – no-op stub
    """Pretend to start an *uvicorn* server – does nothing."""

    raise RuntimeError("The uvicorn stub cannot run a server in the test environment.")


__all__ = ["run"]

