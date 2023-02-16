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

    """SVG Units of measurement."""

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


_UNIT_SPECIFIERS = [x.value[0] for x in Unit]
_UNIT_SPECIFIER2UNIT = {x.value[0]: x for x in Unit}

_NUMBER = r"([-+]?[0-9]+(\.[0-9]*)?|[-+]?\.[0-9]+)([eE][-+]?[0-9]+)?"
_UNIT_RE = re.compile(rf"(?P<unit>{'|'.join(_UNIT_SPECIFIERS)})")
_NUMBER_RE = re.compile(rf"(?P<number>{_NUMBER})")
_UNIT_AND_NUMBER_RE = re.compile(rf"^{_NUMBER_RE.pattern}{_UNIT_RE.pattern}$")


def _parse_unit(value: str) -> tuple[float, str]:
    """Split the value and unit from a string.

    :param value: The value to parse (e.g. "55.32px")
    :param default_unit: The unit to use if none is specified (e.g. "px")
    :return: A tuple of the value and unit specifier
    :raise ValueError: If the value cannot be parsed

    Take a value such as "55.32px" and return (55.32, 'px'). Preserves non-units, so
    "55.32" returns (55.32, ""). These are actually pixels, but you don't want "px"
    in your viewbox calls. It is best to work in non-specified "user units" and then
    set the svg width and height to an specified unit. Within the function, "55.32"
    would be identified as "fully_specified".
    """
    if fully_specified := _UNIT_AND_NUMBER_RE.match(str(value)):
        return float(fully_specified["number"]), fully_specified["unit"]
    msg = f"Cannot parse value and unit from {value}"
    raise ValueError(msg)


@dataclasses.dataclass
class Measurement:

    """Measurement with unit of measurement.

    Converts to and stores the value in user units. Also retains the input units so
    you can update the value then convert back.
    """

    value: float
    native_unit: Unit

    def __init__(self, measurement: float | str) -> None:
        """Create a measurement from a string or float.

        :param measurement: a float (user units) or string with unit specifier.
        :raises ValueError: if the input units cannot be identified
        """
        if isinstance(measurement, (float, int)):
            self.value = measurement
            self.native_unit = Unit.USER
        else:
            value, unit_specifier = _parse_unit("0" + measurement)
            self.native_unit = _UNIT_SPECIFIER2UNIT[unit_specifier]
            self.value = value * self.native_unit.value[1]

    def set_value(self, value: float) -> None:
        """Set the value of the measurement in user units.

        :param value: the new value in user units
        """
        self.value = value

    def _get_float_as(self, unit: Unit) -> float:
        """Get the measurement in the specified unit.

        :param unit: the unit to convert to
        :return: the measurement in the specified unit
        """
        return self.value / unit.value[1]

    def get_as(self, unit: Unit) -> str:
        """Get the measurement in the specified unit.

        :param unit: the unit to convert to
        :return: the measurement in the specified unit, always as a string
        """
        value = self._get_float_as(unit)
        return f"{format_number(value)}{unit.value[0]}"

    @property
    def native(self) -> str:
        """Get the value in the native unit.

        :return: self.value in initial unit used to init Measurement instance
        """
        return self.get_as(self.native_unit)
