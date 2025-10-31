"""Math and conversion for svg-style transformation matrices.

:author: Shay Hill
:created: 2024-05-05
"""

from __future__ import annotations

import numbers
import re
from contextlib import suppress
from typing import TYPE_CHECKING, TypeAlias, cast

from svg_ultralight.strings import svg_matrix

if TYPE_CHECKING:
    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )


RE_MATRIX = re.compile(r"matrix\(([^)]+)\)")

_Matrix: TypeAlias = tuple[float, float, float, float, float, float]


def mat_dot(mat1: _Matrix, mat2: _Matrix) -> _Matrix:
    """Matrix multiplication for svg-style matrices.

    :param mat1: transformation matrix (sx, 0, 0, sy, tx, ty)
    :param mat2: transformation matrix (sx, 0, 0, sy, tx, ty)

    Svg uses an unusual matrix format. For 3x3 transformation matrix

    [[00, 01, 02],
     [10, 11, 12],
     [20, 21, 22]]

    The svg matrix is
    (00, 10, 01, 11, 02, 12)

    Values 10 and 01 are only used for skewing, which is not supported by a bounding
    box. Values 00 and 11 will always be identical for symmetric scaling, which is
    the only scaling implemented in my BoundingBox classes. However, all six values
    are implemented in case this function is used in other contexts.
    """
    aa = sum(mat1[x] * mat2[y] for x, y in ((0, 0), (2, 1)))
    bb = sum(mat1[x] * mat2[y] for x, y in ((1, 0), (3, 1)))
    cc = sum(mat1[x] * mat2[y] for x, y in ((0, 2), (2, 3)))
    dd = sum(mat1[x] * mat2[y] for x, y in ((1, 2), (3, 3)))
    ee = sum(mat1[x] * mat2[y] for x, y in ((0, 4), (2, 5))) + mat1[4]
    ff = sum(mat1[x] * mat2[y] for x, y in ((1, 4), (3, 5))) + mat1[5]
    return (aa, bb, cc, dd, ee, ff)


def mat_apply(matrix: _Matrix, point: tuple[float, float]) -> tuple[float, float]:
    """Apply an svg-style transformation matrix to a point.

    :param mat1: transformation matrix (a, b, c, d, e, f) describing a 3x3 matrix
        with an implied third row of (0, 0, 1)
        [[a, c, e], [b, d, f], [0, 0, 1]]
    :param mat2: point (x, y)
    """
    a, b, c, d, e, f = matrix
    x, y = point
    result_x = a * x + c * y + e
    result_y = b * x + d * y + f
    return result_x, result_y


def mat_invert(tmat: _Matrix) -> _Matrix:
    """Invert a 2D transformation matrix in svg format."""
    a, b, c, d, e, f = tmat
    det = a * d - b * c
    if det == 0:
        msg = "Matrix is not invertible"
        raise ValueError(msg)
    return (
        d / det,
        -b / det,
        -c / det,
        a / det,
        (c * f - d * e) / det,
        (b * e - a * f) / det,
    )


def get_transform_matrix(elem: EtreeElement) -> _Matrix:
    """Get the transformation matrix from an svg element.

    :param element: svg element
    """
    transform = elem.attrib.get("transform")
    if not transform:
        return (1, 0, 0, 1, 0, 0)
    values_str = ""
    with suppress(AttributeError):
        values_str = cast("re.Match[str]", RE_MATRIX.match(transform)).group(1)
    with suppress(ValueError):
        aa, bb, cc, dd, ee, ff = (float(val) for val in values_str.split())
        return (aa, bb, cc, dd, ee, ff)
    msg = f"Could not parse transformation matrix from {transform}"
    raise ValueError(msg)


def new_transformation_matrix(
    transformation: _Matrix | None = None,
    *,
    scale: tuple[float, float] | float | None = None,
    dx: float | None = None,
    dy: float | None = None,
) -> _Matrix:
    """Create a new transformation matrix.

    This takes the standard arguments in the BoundingBox classes and returns an
    svg-style transformation matrix.
    """
    transformation = transformation or (1, 0, 0, 1, 0, 0)

    if isinstance(scale, (float, int, numbers.Real)):
        scale_x, scale_y = (scale, scale)
    elif scale is None:
        scale_x, scale_y = (1, 1)
    else:
        scale_x, scale_y = scale

    dx = dx or 0
    dy = dy or 0
    return mat_dot((float(scale_x), 0, 0, float(scale_y), dx, dy), transformation)


def transform_element(
    elem: EtreeElement, matrix: _Matrix, *, reverse: bool = False
) -> EtreeElement:
    """Apply a transformation matrix to an svg element.

    :param elem: svg element
    :par m matrix: transformation matrix

    :param reverse: If you have a transformation matrix, A, and wish to apply an
    additional transform, B, the result is B @ A. This is how an element can be
    cumulatively transformed in svg.

    If the element is transformed by A and is a part of a GROUP transformed by B,
    then the result is the reverse: A @ B.
    """
    current = get_transform_matrix(elem)
    if reverse:
        elem.attrib["transform"] = svg_matrix(mat_dot(current, matrix))
    else:
        elem.attrib["transform"] = svg_matrix(mat_dot(matrix, current))
    return elem
