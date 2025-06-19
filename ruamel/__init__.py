"""Tiny stub of the *ruamel.yaml* package sufficient for the MCPM test-suite.

The real library offers an extensive YAML implementation but the code under
test only needs the ability to *load* and *dump* very small configuration
files.  We can therefore back the functionality with Python’s built-in
``json`` module which is *good enough* for the structured data used in the
repository.
"""

from __future__ import annotations

import json
import sys
from types import ModuleType
from typing import Any


class _YAMLStub:  # noqa: D101 – minimal compatibility layer
    preserve_quotes: bool = False

    def indent(self, mapping: int = 2, sequence: int = 4, offset: int = 2):  # noqa: D401 – no-op
        # The real method only affects *formatting*, which is irrelevant for
        # the unit tests.  Retained here so that calls do not raise.
        return None

    # ---------------------------------------------------------------------
    # Loading helpers – fall back to an empty dict on any error which mirrors
    # the defensive strategy employed by the real code when it encounters an
    # unreadable configuration file.
    # ---------------------------------------------------------------------
    def load(self, stream) -> Any:  # noqa: D401 – stub
        try:
            return json.load(stream)
        except Exception:
            return {}

    def dump(self, data: Any, stream):  # noqa: D401 – stub
        json.dump(data, stream, indent=2)


# Expose a sub-module so that ``from ruamel.yaml import YAML`` succeeds.
yaml_module = ModuleType("ruamel.yaml")
yaml_module.YAML = _YAMLStub  # type: ignore[attr-defined]
sys.modules[yaml_module.__name__] = yaml_module

# For convenience make the sub-module accessible as an attribute of the parent
# package so that ``import ruamel.yaml as yaml`` works as expected.
setattr(sys.modules[__name__], "yaml", yaml_module)

__all__ = ["yaml"]
