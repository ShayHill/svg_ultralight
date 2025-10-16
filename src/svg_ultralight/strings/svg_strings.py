"""Explicit string formatting calls for arguments that aren't floats or strings.

:author: Shay Hill
:created: 10/30/2020

The `string_conversion` module will format floats or strings. Some other formatters can
make things easier.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from svg_ultralight.string_conversion import format_number

if TYPE_CHECKING:
    from collections.abc import Iterable


_MAX_8BIT = 255
_BIG_INT = 2**32 - 1


def _float_to_8bit_int(clipped_float: float) -> int:
    """Convert a float between 0 and 255 to an int between 0 and 255.

    :param float_: a float in the closed interval [0 .. 255]. Values outside this
        range will be clipped.
    :return: an int in the closed interval [0 .. 255]

    Convert color floats [0 .. 255] to ints [0 .. 255] without rounding, which "short
    changes" 0 and 255.
    """
    clipped_float = min(_MAX_8BIT, max(0, clipped_float))
    if clipped_float % 1:
        high_int = int(clipped_float / _MAX_8BIT * _BIG_INT)
        return high_int >> 24
    return int(clipped_float)


def svg_ints(floats: Iterable[float]) -> str:
    """Space-delimited ints.

    :param floats: and number of floats
    :return: each float rounded to an int, space delimited
    """
    return " ".join(str(round(x)) for x in floats)


def svg_floats(floats: Iterable[float]) -> str:
    """Space-delimited floats.

    :param floats: and number of floats
    :return: each float formatted, space delimited

    matrix strings, svg viewBox, and other attributes need space-delimited floats.
    """
    return " ".join(format_number(x) for x in floats)


def svg_float_tuples(tuples: Iterable[tuple[float, float]]) -> str:
    """Space-delimited tuples.

    :param tuples: [(a, b), (c, d)]
    :return: "a,b c,d"
    """
    tuple_strings = [",".join(format_number(n) for n in t) for t in tuples]
    return " ".join(tuple_strings)


# ===================================================================================
#   Specific string formats
# ===================================================================================


def svg_color_tuple(rgb_floats: tuple[float, float, float]) -> str:
    """Turn an rgb tuple (0-255, 0-255, 0-255) into an svg color definition.

    :param rgb_floats: (0-255, 0-255, 0-255)
    :return: "rgb(128,128,128)"
    """
    r, g, b = map(_float_to_8bit_int, rgb_floats)
    return f"rgb({r},{g},{b})"


def svg_matrix(floats: Iterable[float]) -> str:
    """Create a matrix string for the svg transform attribute.

    a: scale x
    b: skew y
    c: skew x
    d: scale y
    e: translate x
    f: translate y
    :return: "matrix(a,b,c,d,e,f)"

    The matrix() function defines a transformation in the 2D space. The six values
    represent a 3x3 matrix that is used to perform linear transformations such as
    translation, scaling, rotation, and skewing on SVG elements.
    """
    try:
        a, b, c, d, e, f = floats
    except ValueError as e:
        msg = "svg_matrix() needs exactly 6 floats."
        raise ValueError(msg) from e
    return f"matrix({svg_floats((a, b, c, d, e, f))})"
