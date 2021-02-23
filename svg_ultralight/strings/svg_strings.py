#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
"""Explicit string formatting calls for arguments that aren't floats or strings.

:author: Shay Hill
:created: 10/30/2020

The `string_conversion` module will format floats or strings. Some other formatters can
make things easier.
"""

from typing import Iterable, Tuple

from ..string_conversion import format_number


def svg_color_tuple(rgb_floats):
    """
    Turn an rgb tuple (0-255, 0-255, 0-255) into an svg color definition.

    :param rgb_floats: (0-255, 0-255, 0-255)
    :return: "rgb(128,128,128)"
    """
    r, g, b = (round(x) for x in rgb_floats)
    return f"rgb({r},{g},{b})"


def svg_ints(floats: Iterable[float]) -> str:
    """
    Space-delimited ints

    :param floats: and number of floats
    :return: each float rounded to an int, space delimited
    """
    return " ".join(str(round(x)) for x in floats)


def svg_float_tuples(tuples: Iterable[Tuple[float, float]]) -> str:
    """
    Space-delimited tuples

    :param tuples: [(a, b), (c, d)]
    :return: "a,b c,d"
    """
    tuples = [",".join(format_number(x) for x in y) for y in tuples]
    return " ".join(tuples)
