"""Convert between absolute units.

Model everything in user units, then use "width" and "height" in the svg root element
to scale these units to the desired size.

I borrowed test values and and conventions from Inkscape's `inkek.units.py`.

:author: Shay Hill
:created: 2023-02-12
"""

from __future__ import annotations

import dataclasses
import enum
import re
from contextlib import suppress
from typing import Any, Literal, TypeAlias, cast

from svg_ultralight.string_conversion import format_number

# units per inch
_UPI = 96

# units per centimeter
_UPC = 96 / 2.54


class Unit(enum.Enum):
    """SVG Units of measurement.

    Value is (unit conversion, unit specifier)

    The unit specifier string are how various units are identified in SVG.
    e.g., "44in"
    """

    IN = "in", _UPI  # inches
    PT = "pt", 4 / 3  # points
    PX = "px", 1  # pixels
    MM = "mm", _UPC / 10  # millimeters
    CM = "cm", _UPC  # centimeters
    M = "m", _UPC * 100  # meters
    KM = "km", _UPC * 100000  # kilometers
    Q = "Q", _UPC / 40  # quarter-millimeters
    PC = "pc", _UPI / 6  # picas
    YD = "yd", _UPI * 36  # yards
    FT = "ft", _UPI * 12  # feet
    USER = "", 1  # "user units" without a unit specifier


_UnitSpecifier: TypeAlias = Literal[
    "in", "pt", "px", "mm", "cm", "m", "km", "Q", "pc", "yd", "ft", ""
]


_UNIT_SPECIFIER2UNIT = {x.value[0]: x for x in Unit}

_UNIT_SPECIFIERS = [x.value[0] for x in Unit]
_NUMBER = r"([-+]?[0-9]+(\.[0-9]*)?|[-+]?\.[0-9]+)([eE][-+]?[0-9]+)?"
_UNIT_RE = re.compile(rf"(?P<unit>{'|'.join(_UNIT_SPECIFIERS)})$")
_NUMBER_RE = re.compile(rf"(?P<number>{_NUMBER})")
_NUMBER_AND_UNIT = re.compile(rf"^{_NUMBER_RE.pattern}{_UNIT_RE.pattern}$")


def is_measurement_arg(obj: object) -> bool:
    """Determine if an object is a valid measurement argument.

    :param obj: object to check
    :return: True if the object is a valid measurement argument
    """
    maybe_measurement_arg = cast("Any", obj)
    with suppress(ValueError):
        _ = Measurement(maybe_measurement_arg)
        return True
    return False


def _parse_unit(measurement_arg: MeasurementArg) -> tuple[float, Unit]:
    """Split the value and unit from a string.

    :param measurement_arg: The value to parse (e.g. "55.32px")
    :return: A tuple of the value and Unit
    :raise ValueError: If the value cannot be parsed

    Take a value such as "55.32px" and return (55.32, Unit.PX). Preserves non-units,
    so "55.32" returns (55.32, Unit.USER) These are actually pixels, but you don't
    want "px" in your viewbox calls. It is best to work in non-specified "user units"
    and then set the svg width and height to an specified unit.

    Can handle a lot of args:

    | arg type      | example            | result             |
    | ------------- | ------------------ | ------------------ |
    | float         | 55.32              | (55.32, Unit.USER) |
    | str           | "55.32px"          | (55.32, Unit.PX)   |
    | str           | "55.32"            | (55.32, Unit.USER) |
    | str           | "px"               | (0.0, Unit.PX)     |
    | (str, str)    | ("55.32", "px")    | (55.32, Unit.PX)   |
    | (float, str)  | (55.32, "px")      | (55.32, Unit.PX)   |
    | (str, Unit)   | ("55.32", Unit.PX) | (55.32, Unit.PX)   |
    | (float, Unit) | (55.32, Unit.PX)   | (55.32, Unit.PX)   |
    | Unit          | Unit.PX            | (0.0, Unit.PX)     |
    | Measurement   | Measurement("3in") | (3.0, Unit.IN)     |

    """
    if isinstance(measurement_arg, Measurement):
        return measurement_arg.get_tuple()
    failure_msg = f"Cannot parse value and unit from {measurement_arg}"
    unit: _UnitSpecifier | Unit
    try:
        if isinstance(measurement_arg, tuple):
            number, unit = float(measurement_arg[0]), measurement_arg[1]
            if isinstance(unit, Unit):
                return number, unit
            return number, _UNIT_SPECIFIER2UNIT[unit]

        if isinstance(measurement_arg, (int, float)):
            return _parse_unit((measurement_arg, ""))

        if isinstance(measurement_arg, Unit):
            return _parse_unit((0, measurement_arg))

        if number_unit := _NUMBER_AND_UNIT.match(measurement_arg):
            unit = _UNIT_SPECIFIER2UNIT[number_unit["unit"]]
            return _parse_unit((number_unit["number"], unit))

        if unit_only := _UNIT_RE.match(measurement_arg):
            unit = _UNIT_SPECIFIER2UNIT[unit_only["unit"]]
            return _parse_unit((0, unit))

    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise ValueError(failure_msg) from e

    raise ValueError(failure_msg)


@dataclasses.dataclass
class Measurement:
    """Measurement with unit of measurement.

    Converts to and stores the value in user units. Also retains the input units so
    you can update the value then convert back.
    """

    value: float
    native_unit: Unit

    def __init__(self, measurement_arg: MeasurementArg) -> None:
        """Create a measurement from a string or float.

        :param measurement_arg: a float (user units) or string with unit specifier.
        :raises ValueError: if the input units cannot be identified
        """
        value, self.native_unit = _parse_unit(measurement_arg)
        self.value = value * self.native_unit.value[1]

    def __float__(self) -> float:
        """Get the measurement in user units.

        :return: value in user units

        It's best to do all math with self.value, but this is here for conversion
        with less precision loss.
        """
        return self.value

    def get_value(self, unit: Unit | None = None) -> float:
        """Get the measurement in the specified unit.

        :param unit: optional unit to convert to
        :return: value in specified units

        It's best to do all math with self.value, but this is here for conversion
        with less precision loss.
        """
        if unit is None:
            return self.value
        if isinstance(unit, str):
            unit = _UNIT_SPECIFIER2UNIT[unit]
        return self.value / unit.value[1]

    def get_tuple(self, unit: Unit | None = None) -> tuple[float, Unit]:
        """Get the measurement as a tuple of value and unit.

        :param unit: optional unit to convert to
        :return: value in specified as a tuple
        """
        return self.get_value(unit), unit or Unit.USER

    def get_str(self, unit: Unit | None = None) -> str:
        """Get the measurement in the specified unit as a string.

        :param optional unit: the unit to convert to
        :return: the measurement in the specified unit as a string

        The input arguments for groups of measurements are less flexible than for
        single measurements. Single measurements can be defined by something like
        `(1, "in")`, but groups can be passed as single or tuples, so there is no way
        to differentiate between (1, "in") and "1in" or (1, "in") as ("1", "0in").
        That is a limitation, but doing it that way preserved the flexibility (and
        backwards compatibility) of being able to define padding as "1in" everywhere
        or (1, 2, 3, 4) for top, right, bottom, left.

        The string from this method is different from the string in the `get_svg`
        method, because this string will print a full printable precision, while the
        svg string will print a reduced precision. So this string can be used to as
        an argument to pad or print_width without losing precision.
        """
        value, unit = self.get_tuple(unit)
        return f"{value}{unit.value[0]}"

    def get_svg(self, unit: Unit | None = None) -> str:
        """Get the measurement in the specified unit as it would be written in svg.

        :param optional unit: the unit to convert to (defaults to native unit)
        :return: the measurement in the specified unit, always as a string

        Rounds values to 6 decimal places as recommended by svg guidance online.
        Higher resolution just changes file size without imroving quality.
        """
        _, unit = self.get_tuple(unit or self.native_unit)
        value_as_str = format_number(self.get_value(unit))
        return f"{value_as_str}{unit.value[0]}"

    def __add__(self, other: Measurement | float) -> Measurement:
        """Add two measurements.

        :param other: the other measurement
        :return: the sum of the two measurements in self native unit
        """
        result = Measurement(self.native_unit)
        result.value = self.value + float(other)
        return result

    def __radd__(self, other: float) -> Measurement:
        """Add a measurement to a float.

        :param other: the other measurement
        :return: the sum of the two measurements in self native unit
        """
        return self.__add__(other)

    def __sub__(self, other: Measurement | float) -> Measurement:
        """Subtract two measurements.

        :param other: the other measurement
        :return: the difference of the two measurements in self native unit
        """
        return self.__add__(-other)

    def __rsub__(self, other: float) -> Measurement:
        """Subtract a measurement from a float.

        :param other: the other measurement
        :return: the difference of the two measurements in self native unit
        """
        return self.__mul__(-1).__add__(other)

    def __mul__(self, scalar: float) -> Measurement:
        """Multiply a measurement by a scalar.

        :param scalar: the scalar to multiply by
        :return: the measurement multiplied by the scalar in self native unit
        """
        result = Measurement(self.native_unit)
        result.value = self.value * scalar
        return result

    def __rmul__(self, scalar: float) -> Measurement:
        """Multiply a measurement by a scalar.

        :param scalar: the scalar to multiply by
        :return: the measurement multiplied by the scalar in self native unit
        """
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Measurement:
        """Divide a measurement by a scalar.

        :param scalar: the scalar to divide by
        :return: the measurement divided by the scalar in self native unit
        """
        return self.__mul__(1.0 / scalar)

    def __neg__(self) -> Measurement:
        """Negate a measurement.

        :return: the negated measurement in self native unit
        """
        return self.__mul__(-1)


def to_user_units(measurement_arg: MeasurementArg) -> float:
    """Convert a measurement argument to user units.

    :param measurement_arg: The measurement argument to convert
    :return: The measurement in user units
    """
    if isinstance(measurement_arg, (int, float)):
        return float(measurement_arg)
    return Measurement(measurement_arg).value


def to_svg_str(measurement_arg: MeasurementArg) -> str:
    """Convert a measurement argument to an svg string.

    :param measurement_arg: The measurement argument to convert
    :return: The measurement as an svg string
    """
    return Measurement(measurement_arg).get_svg()


# the arguments this module will attempt to interpret as a string with a unit specifier
MeasurementArg: TypeAlias = (
    float
    | str
    | tuple[str, _UnitSpecifier]
    | tuple[float, _UnitSpecifier]
    | tuple[str, Unit]
    | tuple[float, Unit]
    | Unit
    | Measurement
)
