"""Convert between absolute units.

:author: Shay Hill
:created: 2023-02-12
"""
import dataclasses
import enum
import re

from svg_ultralight.string_conversion import format_number

RE_UNIT = re.compile(r"(?P<value>.*\d)(?P<unit>[a-z]*)$")


class UnitOfMeasurement(enum.Enum):

    """SVG Units of measurement."""

    USER_UNITS = ("", 1)
    INCHES = ("in", 96)
    CENTIMETERS = ("cm", 96 / 2.54)
    MILLIMETERS = ("mm", 96 / 25.4)


@dataclasses.dataclass
class Measurement:

    """Measurement with unit of measurement.

    Converts to and stores the value in user units. Also retains the input units so
    you can scale or add then convert.
    """

    value: float
    native_unit: UnitOfMeasurement

    def __init__(self, measurement: float | str) -> None:
        """Create a measurement from a string or float.

        :param measurement: a float (user units) or string with units. Supports
            "0in", "0cm", "0mm", "0"
        :raises ValueError: if the input units cannot be identified
        """
        match_measurement = RE_UNIT.match(str(measurement))
        if match_measurement is None:
            msg = f"cannot parse measurement: {measurement}"
            raise ValueError(msg)

        unit = match_measurement["unit"]
        try:
            self.native_unit = next(x for x in UnitOfMeasurement if x.value[0] == unit)
        except StopIteration as e:
            msg = f"unknown unit of measurement: '{unit}'"
            raise ValueError(msg) from e

        self.value = float(match_measurement["value"]) * self.native_unit.value[1]

    def set_value(self, value: float) -> None:
        """Set the value of the measurement in user units.

        :param value: the new value in user units
        """
        self.value = value

    def get_as(self, unit: UnitOfMeasurement) -> str:
        """Get the measurement in the specified unit.

        :param unit: the unit to convert to
        :return: the measurement in the specified unit, always as a string
        """
        value = self.value / unit.value[1]
        return f"{format_number(value)}{unit.value[0]}"

    @property
    def native(self) -> str:
        """Get the value in the native unit.

        :return: self.value in initial unit used to init Measurement instance
        """
        return self.get_as(self.native_unit)

    @property
    def inches(self) -> str:
        """Get the value in inches.

        :return: self.value in inches as a string "0.0in"
        """
        return self.get_as(UnitOfMeasurement.INCHES)

    @property
    def centimeters(self) -> str:
        """Get the value in centimeters.

        :return: self.value in centimeters as a string "0.0cm"
        """
        return self.get_as(UnitOfMeasurement.CENTIMETERS)

    @property
    def millimeters(self) -> str:
        """Get the value in millimeters.

        :return: self.value in millimeters as a string "0.0mm"
        """
        return self.get_as(UnitOfMeasurement.MILLIMETERS)
