"""Math and conversion for svg-style transformation matrices.

:author: Shay Hill
:created: 2024-05-05
"""

from __future__ import annotations

import math
import numbers
import re
from contextlib import suppress
from typing import TYPE_CHECKING, TypeAlias

from paragraphs import par

from svg_ultralight.strings import svg_matrix

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from lxml.etree import _Element as EtreeElement

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
    transform = elem.attrib.get("transform", "")
    return transform_to_matrix(transform)


def new_transformation_matrix(
    transformation: _Matrix | None = None,
    *,
    scale: tuple[float, float] | float | None = None,
    dx: float | None = None,
    dy: float | None = None,
) -> _Matrix:
    """Create a new transformation matrix.

    This takes the standard arguments in the BoundingBox classes and returns an
    svg-style transformation matrix. If both scale and dx or dy are provided, the
    scale will be applied first.
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


# ===================================================================================
#   Create a matrix from any svg transform string.
# ===================================================================================


# Check that each command has the correct number of parameters (as I understand the
# svg spec). The values are sets of valid parameter counts for each command.
_REQUIRED_PARAMS = {
    "translate": {1, 2},
    "scale": {1, 2},
    "rotate": {1, 2, 3},
    "skewX": {1},
    "skewY": {1},
    "matrix": {6},
}


def _get_nos(transform: str) -> list[float]:
    """Extract numbers from a transform string."""
    bits = re.split(r"[(),\s]+", transform)
    nos: list[float] = []
    for bit in bits:
        with suppress(ValueError):
            nos.append(float(bit))
    return nos


def _get_nos_error_string(nos: Iterable[float]) -> str:
    """Return a string representation of a list of numbers."""
    nos_ = sorted(map(str, nos))
    if len(nos_) == 1:
        params = "parameter" if nos_[0] == "1" else "parameters"
        return f"exactly {nos_[0]} {params}"
    return f"{', '.join(nos_[:-1])}, or {nos_[-1]} parameters"


def _split_commands(transform: str) -> Iterator[tuple[str, list[float]]]:
    """Parse a transform string into commands and their associated numbers."""
    commands = (x + ")" for x in re.split(r"\s*\)", transform) if x.strip())
    for command in commands:
        name = command.split("(", 1)[0].strip()
        nos = _get_nos(command)
        if name not in _REQUIRED_PARAMS:
            msg = f"Unknown transform command: {name}. In {transform}."
            raise ValueError(msg)
        reqd = _REQUIRED_PARAMS[name]
        if len(nos) not in reqd:
            msg = par(
                f"""{name} requires {_get_nos_error_string}, got {len(nos)} in
                {transform}."""
            )
            raise ValueError(msg)
        yield name, nos


def transform_to_matrix(transform: str) -> _Matrix:
    """Convert any svg transform string to a 6-value matrix.

    1. **Translate**: Moves the element a specified distance along the X and Y axes.
       - Pattern: `translate(x, y)`
       - Example: `translate(30, 50)`
       - Note: If only one parameter is specified, the Y-axis value defaults to 0.

    2. **Scale**: Scales the element in the X and Y direction.
       - Pattern: `scale(sx, sy)`
       - Example: `scale(2, 3)`
       - Note: If only one parameter is specified, it's used for both the X and Y
         scale factors.

    3. **Rotate**: Rotates the element around a specified point.
       - Pattern: `rotate(angle)`
       - Example: `rotate(45)`
       - Pattern with a pivot point: `rotate(angle, cx, cy)`
       - Example: `rotate(45, 100, 100)`
       - Note: The default pivot point is the origin (0, 0).

    4. **SkewX**: Skews the element along the X-axis.
       - Pattern: `skewX(angle)`
       - Example: `skewX(30)`

    5. **SkewY**: Skews the element along the Y-axis.
       - Pattern: `skewY(angle)`
       - Example: `skewY(30)`

    6. **Matrix**: Defines a transformation in terms of a 2D matrix.
       - Pattern: `matrix(a, b, c, d, e, f)`
       - Example: `matrix(1, 0, 0, 1, 30, 50)`
    """
    mats: list[_Matrix] = []
    for name, nos in _split_commands(transform):
        if name == "translate":
            tx, ty, *_ = *nos, 0
            mats.append((1, 0, 0, 1, tx, ty))
            continue
        if name == "scale":
            sx, sy, *_ = *nos, nos[0]
            mats.append((sx, 0, 0, sy, 0, 0))
            continue
        if name == "rotate":
            degs, cx, cy, *_ = *nos, 0, 0
            angle = math.radians(degs)
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            dx = cx - cx * cos_a + cy * sin_a
            dy = cy - cx * sin_a - cy * cos_a
            mats.append((cos_a, sin_a, -sin_a, cos_a, dx, dy))
            continue
        if name == "skewX":
            angle = math.radians(nos[0])
            mats.append((1, 0, math.tan(angle), 1, 0, 0))
            continue
        if name == "skewY":
            angle = math.radians(nos[0])
            mats.append((1, math.tan(angle), 0, 1, 0, 0))
            continue
        if name == "matrix":
            mats.append((nos[0], nos[1], nos[2], nos[3], nos[4], nos[5]))
            continue
    if not mats:
        return (1, 0, 0, 1, 0, 0)
    at_mat = mats[0]
    for mat in mats[1:]:
        at_mat = mat_dot(at_mat, mat)  # svg applies transformations in reverse order
    return at_mat
