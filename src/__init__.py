"""Helper to make ``mcpm`` importable when the package is used in *editable*
mode (i.e. when running directly from the repository root).

The source-code resides in *src/mcpm/*.  Production installations add the
package to *sys.path* via standard packaging mechanisms so ``import mcpm``
works out-of-the-box.  The unit tests, however, import modules using the
namespace package form (``import src.mcpm…``) which leaves the top-level
module name ``mcpm`` undefined.  We therefore insert an alias into
``sys.modules`` so that absolute imports inside the code-base continue to
resolve correctly.
"""

from __future__ import annotations

import sys as _sys


# When *src.mcpm* is imported, the module instance is available under that key
# in ``sys.modules``.  We create a second entry pointing to the same object so
# that ``import mcpm`` works as expected.
# Ensure that the *src* directory itself is on ``sys.path`` so that
# ``import mcpm`` resolves to the local sources during in-repository
# execution (the normal packaging mechanism handles this when the project is
# installed in site-packages).
from pathlib import Path as _Path

_src_root = _Path(__file__).parent
_abs_src_root = str(_src_root.resolve())
if _abs_src_root not in _sys.path:
    _sys.path.insert(0, _abs_src_root)

# If callers have already imported ``src.mcpm`` (the form used by the unit
# tests) expose it under the shorter top-level name as well so that absolute
# imports inside the package continue to succeed.
if "src.mcpm" in _sys.modules and "mcpm" not in _sys.modules:
    _sys.modules["mcpm"] = _sys.modules["src.mcpm"]
