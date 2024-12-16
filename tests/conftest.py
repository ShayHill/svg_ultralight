"""Test configuration for pytest.

:author: Shay Hill
:created: 7/2/2019
"""

from pathlib import Path
from typing import Any

def pytest_assertrepr_compare(config: Any, op: str, left: str, right: str):
    """See full error diffs"""
    if op in ("==", "!="):
        return ["{0} {1} {2}".format(left, op, right)]

TEST_RESOURCES = Path(__file__).parent / "resources"

