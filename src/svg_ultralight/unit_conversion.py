"""Convert between absolute units.

Model everything in user units, then use "width" and "height" in the svg root element
to scale these units to the desired size.

I borrowed test values and and conventions from Inkscape's `inkek.units.py`.

:author: Shay Hill
:created: 2023-02-12
"""
import dataclasses
import enum
import re

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


# the arguments this module will attempt to interpret as a string with a unit specifier
MeasurementArg = (
    float
    | str
    | tuple[str, str]
    | tuple[float, str]
    | tuple[str, Unit]
    | tuple[float, Unit]
)

_UNIT_SPECIFIER2UNIT = {x.value[0]: x for x in Unit}

_UNIT_SPECIFIERS = [x.value[0] for x in Unit]
_NUMBER = r"([-+]?[0-9]+(\.[0-9]*)?|[-+]?\.[0-9]+)([eE][-+]?[0-9]+)?"
_UNIT_RE = re.compile(rf"(?P<unit>{'|'.join(_UNIT_SPECIFIERS)})")
_NUMBER_RE = re.compile(rf"(?P<number>{_NUMBER})")
_NUMBER_AND_UNIT = re.compile(rf"^{_NUMBER_RE.pattern}{_UNIT_RE.pattern}$")


def _parse_unit(measurement_arg: MeasurementArg) -> tuple[float, Unit]:
    """Split the value and unit from a string.

    :param measurement_arg: The value to parse (e.g. "55.32px")
    :return: A tuple of the value and Unit
    :raise ValueError: If the value cannot be parsed

    Take a value such as "55.32px" and return (55.32, Unit.PX). Preserves non-units,
    so "55.32" returns (55.32, Unit.USER) These are actually pixels, but you don't
    want "px" in your viewbox calls. It is best to work in non-specified "user units"
    and then set the svg width and height to an specified unit.
    """
    failure_msg = f"Cannot parse value and unit from {measurement_arg}"
    unit: str | Unit
    try:
        if isinstance(measurement_arg, tuple):
            number, unit = float(measurement_arg[0]), measurement_arg[1]
            if isinstance(unit, Unit):
                return number, unit
            return number, _UNIT_SPECIFIER2UNIT[unit]

        if isinstance(measurement_arg, (int, float)):
            return _parse_unit((measurement_arg, ""))

        if number_unit := _NUMBER_AND_UNIT.match(str(measurement_arg)):
            return _parse_unit((number_unit["number"], number_unit["unit"]))

        if unit_only := _UNIT_RE.match(str(measurement_arg)):
            return _parse_unit((0, unit_only["unit"]))
    except (ValueError, KeyError) as e:
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

    def set_value(self, value: float) -> None:
        """Set the value of the measurement in user units.

        :param value: the new value in user units
        """
        self.value = value

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

    def get_str(self, unit: Unit | None = None) -> str:
        """Get the measurement in the specified unit as it would be written in svg.

        :param optional unit: the unit to convert to
        :return: the measurement in the specified unit, always as a string

        Rounds values to 6 decimal places as recommended by svg guidance online.
        Higher precision just changes file size without imroving quality.
        """
        value = format_number(self.get_value(unit))
        if unit is None:
            return value
        return f"{value}{unit.value[0]}"

    @property
    def native(self) -> str:
        """Get the value in the native unit.

        :return: self.value in initial unit used to init Measurement instance
        """
        return self.get_str(self.native_unit)


def convert_value(measurement_arg: MeasurementArg, unit: Unit) -> float:
    """Get the measurement in the specified unit.

    :param measurement_arg: a measurement string, e.g. "1.2m"
    :param unit: an output unit
    :return: the measurement in the specified unit as a float
    """
    measurement = Measurement(measurement_arg)
    return measurement.get_value(unit)
