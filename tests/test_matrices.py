"""Test transformations of matrices.

:author: Shay Hill
:created: 2024-05-05
"""

import math
import random
from contextlib import suppress

from svg_ultralight.strings import svg_matrix
from svg_ultralight.transformations import (
    mat_apply,
    mat_dot,
    mat_invert,
    transform_to_matrix,
)


class TestMat:
    def test_explicit(self) -> None:
        expect = (31, 46, 12, 22, 10, 14)
        assert mat_dot((1, 2, 3, 4, 5, 6), (7, 8, 9, 1, 2, 1)) == expect

    def test_apply(self) -> None:
        expect = (36, 52)
        assert mat_apply((1, 2, 3, 4, 5, 6), (7, 8)) == expect

    def test_invert(self) -> None:
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
                for x, y in zip(result, identity, strict=True):
                    assert math.isclose(x, y, abs_tol=0.0001)


class TestTransformToMatrix:
    def test_translate_xy(self) -> None:
        assert transform_to_matrix("translate(10, 20)") == (1, 0, 0, 1, 10, 20)

    def test_translate_x(self) -> None:
        assert transform_to_matrix("translate(10)") == (1, 0, 0, 1, 10, 0)

    def test_scale_uniform(self) -> None:
        assert transform_to_matrix("scale(2)") == (2, 0, 0, 2, 0, 0)

    def test_scale_xy(self) -> None:
        assert transform_to_matrix("scale(2, 3)") == (2, 0, 0, 3, 0, 0)

    def test_rotate_0_0(self) -> None:
        expect = svg_matrix((0, 1, -1, 0, 0, 0))
        result = svg_matrix(transform_to_matrix("rotate(90, 0, 0)"))
        assert result == expect

    def test_rotate_x_0(self) -> None:
        por_x = 10
        por_y = 0
        expect = (1, 0, 0, 1, 0, 0)
        expect = mat_dot((1, 0, 0, 1, -por_x, -por_y), expect)
        expect = mat_dot((0, 1, -1, 0, 0, 0), expect)
        expect = mat_dot((1, 0, 0, 1, por_x, por_y), expect)
        result = svg_matrix(transform_to_matrix(f"rotate(90, {por_x})"))
        assert result == svg_matrix(expect)

    def test_rotate_x_y(self) -> None:
        por_x = 10
        por_y = 30
        expect = (1, 0, 0, 1, 0, 0)
        expect = mat_dot((1, 0, 0, 1, -por_x, -por_y), expect)
        expect = mat_dot((0, 1, -1, 0, 0, 0), expect)
        expect = mat_dot((1, 0, 0, 1, por_x, por_y), expect)
        result = svg_matrix(transform_to_matrix(f"rotate(90, {por_x}, {por_y})"))
        assert result == svg_matrix(expect)

    def test_skewx(self) -> None:
        expect = svg_matrix((1, 0, 1, 1, 0, 0))
        result = svg_matrix(transform_to_matrix("skewX(45)"))
        assert result == expect

    def test_skewy(self) -> None:
        expect = svg_matrix((1, 1, 0, 1, 0, 0))
        result = svg_matrix(transform_to_matrix("skewY(45)"))
        assert result == expect

    def test_matrix(self) -> None:
        assert transform_to_matrix("matrix(1, 2, 3, 4, 5, 6)") == (1, 2, 3, 4, 5, 6)

    def test_extra_spaces(self) -> None:
        expect = (8, 16, 24, 32, 40, 48)
        result = transform_to_matrix("  matrix( 1 , 2 , 3 , 4 , 5 , 6 ) scale  (8) ")
        assert result == expect

    def test_multiple_transforms(self) -> None:
        single = "rotate(130, 10, 30)"
        multi = " ".join(
            ["translate(-10, -30)", "rotate(150)", "rotate(-20)", "translate(10, 30)"]
        )
        expect = svg_matrix(transform_to_matrix(single))
        result = svg_matrix(transform_to_matrix(multi))
        assert result == expect

    def test_empty(self) -> None:
        assert transform_to_matrix("") == (1, 0, 0, 1, 0, 0)
