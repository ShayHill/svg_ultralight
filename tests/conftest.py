"""Test configuration for pytest.

:author: Shay Hill
:created: 7/2/2019
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import os


def pytest_assertrepr_compare(
    config: Any, op: str, left: str, right: str
) -> list[str] | None:
    """See full error diffs"""
    del config
    if op in ("==", "!="):
        return [f"{left} {op} {right}"]
    return None


TEST_RESOURCES = Path(__file__).parent / "resources"

INKSCAPE = Path(r"C:\Program Files\Inkscape\bin\inkscape")


def has_inkscape(inkscape: str | os.PathLike[str]) -> bool:
    """Check if Inkscape is available at a path.

    The Inkscape command-line calls require an inkscape executable without a ".exe"
    extension. This will return exists() -> False every time.
    """
    return Path(inkscape).with_suffix(".exe").exists()
