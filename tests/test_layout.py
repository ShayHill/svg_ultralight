"""Test layout and unit-conversion functions.

:author: Shay Hill
:created: 2023-02-16
"""

# pyright: reportUnknownParameterType=false
# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: analyzeUnannotatedFunctions = false
# pyright: reportMissingParameterType = false
# pyright: reportPrivateUsage = false


import itertools as it
import math
from collections.abc import Iterator

import pytest

from svg_ultralight import layout
from svg_ultralight.string_conversion import format_number
from svg_ultralight.unit_conversion import Measurement, Unit, _parse_unit

INKSCAPE_SCALARS = {
    "in": 96.0,
    "pt": 1.3333333333333333,
    "px": 1.0,
    "mm": 3.779527559055118,
    "cm": 37.79527559055118,
    "m": 3779.527559055118,
    "km": 3779527.559055118,
    "Q": 0.94488188976378,
    "pc": 16.0,
    "yd": 3456.0,
    "ft": 1152.0,
    "": 1.0,  # Default px
    "user": 1.0,  # Default px
}


@pytest.fixture(scope="function", params=Unit)
def unit(request) -> Unit:
    return request.param


@pytest.fixture(scope="function", params=it.product(Unit, Unit))
def unit_pair(request) -> Iterator[Unit]:
    return request.param


class TestParseUnit:
    def test_float(self):
        """Test that a float is returned."""
        assert _parse_unit(1.0) == (1, Unit.USER)

    def test_float_str(self):
        """Test that a float is returned."""
        assert _parse_unit("1.0") == (1, Unit.USER)

    def test_float_str_tuple(self):
        """Test that a float is returned."""
        assert _parse_unit((1.0, "")) == (1, Unit.USER)

    def test_str_str_tuple(self):
        """Test that a float is returned."""
        assert _parse_unit(("1.0", "")) == (1, Unit.USER)

    def test_float_unit_tuple(self):
        """Test that a float is returned."""
        assert _parse_unit((1.0, Unit.PX)) == (1, Unit.PX)

    def test_str_unit_tuple(self):
        """Test that a float is returned."""
        assert _parse_unit(("1.0", Unit.PX)) == (1, Unit.PX)

    def test_str_with_unit(self):
        """Test that a float is returned."""
        assert _parse_unit("1.0px") == (1, Unit.PX)


class TestMeasurement:
    def test_unit_identified(self, unit):
        """Test that unit is identified correctly."""
        assert Measurement(f"1{unit.value[0]}").native_unit == unit

    def test_value_scaled(self, unit):
        """Value is scaled per Inkscape conversion values."""
        assert math.isclose(
            Measurement(f"1{unit.value[0]}").value, INKSCAPE_SCALARS[unit.value[0]]
        )

    def test_conversion(self, unit_pair):
        """Test that value is converted to other units."""
        unit_a, unit_b = unit_pair
        a_unit = Measurement(f"1{unit_a.value[0]}")
        a_as_b = a_unit.get_value(unit_b)
        b_unit = Measurement(f"{a_as_b}{unit_b.value[0]}")
        assert math.isclose(b_unit.value, a_unit.value)

    def test_conversion_to_string(self, unit):
        """Test that value is converted to other units."""
        a_unit = Measurement(f"1{unit.value[0]}")
        a_unit.value /= 3
        expected_unit_specifier = unit.value[0]
        expected = f"{format_number(1/3)}{unit.value[0]}"
        assert a_unit.native == expected

    def test_add(self, unit):
        """Test that values are added."""
        a_unit = Measurement(f"1{unit.value[0]}")
        b_unit = Measurement(f"2{unit.value[0]}")
        assert (a_unit + b_unit).value == Measurement(f"3{unit.value[0]}").value

    def test_subtract(self, unit):
        """Test that values are subtracted."""
        a_unit = Measurement(f"1{unit.value[0]}")
        b_unit = Measurement(f"2{unit.value[0]}")
        assert (a_unit - b_unit).value == Measurement(f"-1{unit.value[0]}").value

    def test_multiply(self, unit):
        """Test that values are multiplied."""
        assert (Measurement((1, unit)) * 4).value == Measurement((4, unit)).value

    def test_rmultiply(self, unit):
        """Test that values are multiplied."""
        assert (4 * Measurement((1, unit))).value == Measurement((4, unit)).value

    def test_divide(self, unit):
        """Test that values are multiplied."""
        assert (Measurement((1, unit)) / 4).value == Measurement((1 / 4, unit)).value


class TestLayout:
    def test_standard(self):
        """No print dimensions give expanded pad argument
        and no width args"""
        viewbox = (1, 2, 3, 4)
        padded, width_attribs = layout.pad_and_scale(viewbox, 5)
        assert padded == (-4, -3, 13, 14)
        assert width_attribs == {}

    def test_0_area(self):
        """Zero area viewbox is padded"""
        viewbox = (0, 0, 0, 0)
        padded, width_attribs = layout.pad_and_scale(viewbox, 1)
        assert padded == (-1, -1, 2, 2)

    def test_0_width(self):
        """Test that print width is used to calculate pad"""
        viewbox = (0, 0, 96, 0)
        padded, width_attribs = layout.pad_and_scale(viewbox, "0.25in", "2in")
        assert padded == (-48, -48, 192, 96)
        assert width_attribs == {"width": "2.5in", "height": "0.5in"}

    def test_0_height(self):
        """Test that print width is used to calculate pad"""
        viewbox = (0, 0, 0, 96)
        padded, width_attribs = layout.pad_and_scale(viewbox, "0.25in", None, "2in")
        assert padded == (-48, -48, 96, 192)
        assert width_attribs == {"width": "0.5in", "height": "2.5in"}

    def test_string_padding(self):
        """Test that string padding is converted to float"""
        viewbox = (0, 0, 1, 1)
        padded, width_attribs = layout.pad_and_scale(viewbox, "1in")
        assert padded == (-96, -96, 193, 193)
        assert width_attribs == {}

    def test_print_width(self):
        """Test that print width is used to calculate pad"""
        viewbox = (0, 0, 0, 0)
        padded, width_attribs = layout.pad_and_scale(viewbox, "0.25in", "2in")
        assert padded == (-24, -24, 48, 48)
        assert width_attribs == {"width": "0.5in", "height": "0.5in"}

    def test_width_wins(self):
        """The tighter fit (width or height) should be used"""
        viewbox = (1, 2, 3, 6)
        padded, width_attribs = layout.pad_and_scale(viewbox, 0, 2, 200)
        assert padded == (1, 2, 3, 6)
        assert width_attribs == {"width": "2", "height": "4"}

    def test_height_wins(self):
        """The tighter fit (width or height) should be used"""
        viewbox = (1, 2, 3, 6)
        padded, width_attribs = layout.pad_and_scale(viewbox, 0, 200, 2)
        assert padded == (1, 2, 3, 6)
        assert width_attribs == {"width": "1", "height": "2"}
