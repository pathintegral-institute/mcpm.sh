"""Extremely lightweight stub of the *psutil* package.

Only the functionality required by the MCPM code-base is implemented – most
notably ``pid_exists``.  Any additional attribute access will raise an
``AttributeError`` signalling that the stub should be extended if the need
arises.
"""

from __future__ import annotations


def pid_exists(pid: int) -> bool:  # noqa: D401 – stub always returns *False*
    """Pretend that *pid* does not exist.

    The *real* implementation checks whether the process identifier is alive.
    For the purposes of the unit tests this information is irrelevant –
    returning *False* is the safest default and avoids any platform-specific
    behaviour.
    """

    return False


__all__ = ["pid_exists"]

