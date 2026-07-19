"""Explicit string formatting calls for arguments that aren't floats or strings.

:author: Shay Hill
:created: 10/30/2020

The `string_conversion` module will format floats or strings. Some other formatters can
make things easier.
"""

from __future__ import annotations

import re
from contextlib import suppress
from typing import TYPE_CHECKING, TypeAlias, TypeVar

from svg_ultralight.string_conversion import format_number
from svg_ultralight.transformations import transform_to_matrix

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

_Matrix: TypeAlias = tuple[float, float, float, float, float, float]
_T = TypeVar("_T")

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


def _rstrip_list(vals: list[_T], strip_val: _T) -> None:
    """Strip trailing values from a list in place.

    :param vals: a list of values
    :param strip_val: the value to strip from the end of the list
    """
    while vals and vals[-1] == strip_val:
        _ = vals.pop()


def svg_transform(command: str, floats: Iterable[float] | Iterable[str]) -> str:  # noqa: C901
    """Format one svg transform command, removing meaningless arguments."""
    nos = [format_number(x) for x in floats]
    if command == "rotate" and nos and nos[0] == "0":
        nos = []
    if command in {"translate", "rotate", "skewX", "skewY"}:
        _rstrip_list(nos, "0")
    elif command == "scale":
        if nos[1:] and nos[1:][0] == nos[0]:
            nos = nos[:1]
        _rstrip_list(nos, "1")

    if not nos:
        # command may have been valid, but it's meaningless.
        return ""
    nnos = len(nos)
    if command == "translate" and nnos not in {1, 2}:
        msg = f"translate() needs 1 or 2 arguments, not {nnos}."
        raise ValueError(msg)
    if command == "scale" and nnos not in {1, 2}:
        msg = f"scale() needs 1 or 2 arguments, not {nnos}."
        raise ValueError(msg)
    if command == "rotate" and nnos not in {1, 2, 3}:
        msg = f"rotate() needs 1, 2, or 3 arguments, not {nnos}."
        raise ValueError(msg)
    if command in {"skewX", "skewY"} and nnos != 1:
        msg = f"{command}() needs 1 argument, not {nnos}."
    if command == "matrix" and nnos != 6:
        msg = f"matrix() needs 6 arguments, not {nnos}."
        raise ValueError(msg)
    return f"{command}({' '.join(nos)})"


def svg_transforms(
    *args: tuple[str, Iterable[float]] | tuple[str, Iterable[str]],
) -> str:
    """Format multiple svg transform commands, removing meaningless arguments."""
    cmds = [svg_transform(command, floats) for command, floats in args]
    return " ".join(c for c in cmds if c)


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
    return f"matrix({svg_floats((a, b, c, d, e, f))})"
    """
    try:
        a, b, c, d, e, f = floats
    except ValueError as e:
        msg = "svg_matrix() needs exactly 6 floats."
        raise ValueError(msg) from e
    return svg_transform("matrix", (a, b, c, d, e, f))


def _get_nos(transform: str) -> list[float]:
    """Extract numbers from a transform string."""
    bits = re.split(r"[(),\s]+", transform)
    nos: list[float] = []
    for bit in bits:
        with suppress(ValueError):
            nos.append(float(bit))
    return nos


def _split_commands(transform: str) -> Iterator[tuple[str, list[float]]]:
    """Parse a transform string into commands and their associated numbers."""
    commands = (x + ")" for x in re.split(r"\s*\)", transform) if x.strip())
    for command in commands:
        name = command.split("(", 1)[0].strip()
        nos = _get_nos(command)
        yield name, nos


_IDENTITY_STR = svg_matrix((1, 0, 0, 1, 0, 0))


def shortest_transform_string(transform: str | _Matrix) -> str:
    """Return the shortest equivalent transform string.

    This won't try to unwind rotations or skew, but every transformation (x, 0, 0, y,
    a, b) can be expressed as a translate and scale. If scale is 1 or translate is 0,
    this can be shorter than a matrix string. Also passes short commands like
    `rotate(90)` through unchanged.

    But it won't spoil nice, short input arguments like 'skewX(45)' either.

    This does let through a few odd cases like "skewX(1) skewX(1)" which is short but
    not the shortest.
    """
    native: str | None = None
    if isinstance(transform, str):
        native = svg_transforms(*_split_commands(transform))
        if not native:
            return ""
        matrix = svg_matrix(transform_to_matrix(transform))
    else:
        matrix = svg_matrix(transform)
    if matrix == _IDENTITY_STR:
        return ""
    a, b, c, d, e, f = matrix[7:-1].split(" ")
    if (b, c) != ("0", "0"):  # rotation or skew
        return matrix
    cmd_rep = svg_transforms(("translate", (e, f)), ("scale", (a, d)))
    if native is None:
        native = cmd_rep + "$"
    return min(matrix, cmd_rep, native, key=len)
