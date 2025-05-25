"""Test transformations of matrices.

:author: Shay Hill
:created: 2024-05-05
"""

from svg_ultralight.transformations import mat_dot, mat_apply, mat_invert
import random
import math
from contextlib import suppress


class TestMat:
    def test_explicit(self):
        expect = (31, 46, 12, 22, 10, 14)
        assert mat_dot((1, 2, 3, 4, 5, 6), (7, 8, 9, 1, 2, 1)) == expect

    def test_apply(self):
        expect = (36, 52)
        assert mat_apply((1, 2, 3, 4, 5, 6), (7, 8)) == expect

    def test_invert(self):
        identity = (1, 0, 0, 1, 0, 0)
        for _ in range(10):
            tmat = (
                random.randint(-10, 10),
                random.randint(-10, 10),
                random.randint(-10, 10),
                random.randint(-10, 10),
                random.randint(-10, 10),
                random.randint(-10, 10),
            )
            with suppress(ValueError):
                result = mat_dot(tmat, mat_invert(tmat))
                for x, y in zip(result, identity):
                    assert math.isclose(x, y, abs_tol=0.0001)
