"""Expand the pad argument to a tuple of (top, bottom, left, right) values.

:author: Shay Hill
:created: 2023-02-12
"""
from collections.abc import Sequence
from typing import Any, TypeGuard

from svg_ultralight.unit_conversion import Measurement

PadArg = float | str | Sequence[float | str] | Sequence[float] | Sequence[str]


def _is_sequence(arg: object) -> TypeGuard[Sequence[Any]]:
    """Return True if arg is a sequence type, False otherwise.

    :param arg: object to test
    :return: True if arg is a sequence type, False otherwise
    """
    return isinstance(arg, (list, tuple))


def expand_pad_arg(
    pad: PadArg, scale: float | None = None
) -> tuple[float, float, float, float]:
    """Transform a single value or tuple of values to a 4-tuple of user units.

    :param pad: padding value(s) -- 0.5, "0.5", "0.5in", "0.5cm", "0.5mm", or tuple
        of any of these
    :param scale: scale factor to apply to padding values, default 1
    :return: 4-tuple of padding values in (scaled) user units
    """
    scale = scale or 1
    if _is_sequence(pad):
        as_units = [Measurement(p).value * scale for p in pad]
    else:
        as_units = [Measurement(str(pad)).value * scale]
    as_units = [as_units[i % len(as_units)] for i in range(4)]
    return as_units[0], as_units[1], as_units[2], as_units[3]
