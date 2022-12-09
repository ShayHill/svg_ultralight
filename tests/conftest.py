"""Test configuration for pytest.

:author: Shay Hill
:created: 7/2/2019
"""

def pytest_assertrepr_compare(config, op, left, right):
    """See full error diffs"""
    if op in ("==", "!="):
        return ["{0} {1} {2}".format(left, op, right)]


