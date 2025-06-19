"""Package *shim* that re-exports the real implementation located under
``src/mcpm`` so that both

    import mcpm.something

and

    import src.mcpm.something

work in development environments where the project is executed directly from
the repository without an installation step.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType


# Import the actual implementation package.
# Treat this shim as a *namespace package* that points to the real source
# directory so that ``import mcpm.core…`` works while we are still executing
# inside this very ``__init__`` *before* the actual import below completes.

from pathlib import Path as _Path

__path__: list[str] = [str((_Path(__file__).parent.parent / "src" / "mcpm").resolve())]

# Import the production package now that the search path is configured.
_real_pkg = importlib.import_module("src.mcpm")

# Re-export all public attributes.
globals().update(_real_pkg.__dict__)

# Ensure that sub-modules imported via ``src.mcpm.X`` are also visible under the
# shorter alias so that a single instance exists in *sys.modules*.
for _name, _module in list(sys.modules.items()):
    if _name.startswith("src.mcpm"):
        alias = _name.replace("src.mcpm", "mcpm", 1)
        sys.modules[alias] = _module


# Let static analysers know we export *everything* from the real package.
__all__: list[str] = [name for name in dir(_real_pkg) if not name.startswith("__")]
