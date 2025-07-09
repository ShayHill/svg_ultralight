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
    "pt": 4.0 / 3.0,
    "px": 1.0,
    "mm": 96.0 / 25.4,
    "cm": 960.0 / 25.4,
    "m": 96000.0 / 25.4,
    "km": 96000000.0 / 25.4,
    "Q": 24.0 / 25.4,
    "pc": 16.0,
    "yd": 3456.0,
    "ft": 1152.0,
    "": 1.0,  # Default px
    "user": 1.0,  # Default px
}


@pytest.fixture(params=Unit)
def unit(request: pytest.FixtureRequest) -> Unit:
    return request.param


@pytest.fixture(params=it.product(Unit, Unit))
def unit_pair(request: pytest.FixtureRequest) -> Iterator[Unit]:
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
    def test_unit_identified(self, unit: Unit):
        """Test that unit is identified correctly."""
        assert Measurement(f"1{unit.value[0]}").native_unit == unit

    def test_value_scaled(self, unit: Unit):
        """Value is scaled per Inkscape conversion values."""
        assert math.isclose(
            Measurement(f"1{unit.value[0]}").value, INKSCAPE_SCALARS[unit.value[0]]
        )

    def test_conversion(self, unit_pair: tuple[Unit, Unit]):
        """Test that value is converted to other units."""
        unit_a, unit_b = unit_pair
        a_unit = Measurement(f"1{unit_a.value[0]}")
        a_as_b = a_unit.get_value(unit_b)
        b_unit = Measurement(f"{a_as_b}{unit_b.value[0]}")
        assert math.isclose(b_unit.value, a_unit.value)

    def test_add(self, unit: Unit):
        """Test that values are added."""
        a_unit = Measurement(f"1{unit.value[0]}")
        b_unit = Measurement(f"2{unit.value[0]}")
        assert (a_unit + b_unit).value == Measurement(f"3{unit.value[0]}").value

    def test_subtract(self, unit: Unit):
        """Test that values are subtracted."""
        a_unit = Measurement(f"1{unit.value[0]}")
        b_unit = Measurement(f"2{unit.value[0]}")
        assert (a_unit - b_unit).value == Measurement(f"-1{unit.value[0]}").value

    def test_multiply(self, unit: Unit):
        """Test that values are multiplied."""
        assert (Measurement((1, unit)) * 4).value == Measurement((4, unit)).value

    def test_rmultiply(self, unit: Unit):
        """Test that values are multiplied."""
        assert (4 * Measurement((1, unit))).value == Measurement((4, unit)).value

    def test_divide(self, unit: Unit):
        """Test that values are multiplied."""
        assert (Measurement((1, unit)) / 4).value == Measurement((1 / 4, unit)).value


class TestExpandPadArg:
    def test_expand_val(self):
        """Test that a single value is expanded to a 4-tuple."""
        assert layout.expand_pad_arg(1) == (1, 1, 1, 1)

    def test_expand_1tuple(self):
        """Test that a single value is expanded to a 4-tuple."""
        assert layout.expand_pad_arg(1) == (1, 1, 1, 1)

    def test_expand_2tuple(self):
        """Test that a single value is expanded to a 4-tuple."""
        assert layout.expand_pad_arg((1, 2)) == (1, 2, 1, 2)

    def test_expand_3tuple(self):
        """Test that a single value is expanded to a 4-tuple per css rules."""
        assert layout.expand_pad_arg((1, 2, 3)) == (1, 2, 3, 2)

    def test_expand_4tuple(self):
        """Test that a single value is expanded to a 4-tuple per css rules."""
        assert layout.expand_pad_arg((1, 2, 3, 4)) == (1, 2, 3, 4)


class TestLayout:
    def test_standard(self):
        """No print dimensions give expanded pad argument
        and no width args"""
        viewbox = (1, 2, 3, 4)
        padded, width_attribs = layout.pad_and_scale(viewbox, 5)
        assert padded == (-4, -3, 13, 14)
        assert width_attribs == {}

    def test_from_svg_drawings(self):
        """This one doesn't look right in the project.

        Run here to see if there is a bug.
        """
        viewbox = (0, 0, 100, 50)
        pad = ("1in", "1in", "1in", "1in")
        padded, width_attribs = layout.pad_and_scale(viewbox, pad, "pt")
        assert padded == (-72.0, -72.0, 244.0, 194.0)
        assert width_attribs == {"width": "244pt", "height": "194pt"}

    def test_0_area(self):
        """Zero area viewbox is padded"""
        viewbox = (0, 0, 0, 0)
        padded, width_attribs = layout.pad_and_scale(viewbox, 1)
        assert padded == (-1, -1, 2, 2)

    def test_0_width(self):
        """Test that print width is used to calculate pad"""
        viewbox = (0, 0, 96, 0)
        padded, width_attribs = layout.pad_and_scale(viewbox, "0.25in", "2in")
        assert padded == (-12, -12, 120, 24)
        assert width_attribs == {"width": "2.5in", "height": ".5in"}

    def test_0_height(self):
        """Test that print width is used to calculate pad"""
        viewbox = (0, 0, 0, 96)
        padded, width_attribs = layout.pad_and_scale(viewbox, "0.25in", None, "2in")
        assert padded == (-12, -12, 24, 120)
        assert width_attribs == {"width": ".5in", "height": "2.5in"}

    def test_string_padding(self):
        """Test that string padding is converted to float"""
        viewbox = (0, 0, 1, 1)
        padded, width_attribs = layout.pad_and_scale(viewbox, "1in")
        assert padded == (-96, -96, 193, 193)
        assert width_attribs == {}

    def test_infinite_width(self):
        """Raise ValueError if no non-infinite scale can be inferred."""
        viewbox = (0, 0, 0, 0)
        with pytest.raises(ValueError, match="infinite"):
            _ = layout.pad_and_scale(viewbox, "0.25in", "2in")

    def test_pad_print_at_input_scale(self):
        """Test that padding is applied at the input scale.

        Padding get small as scale of user units increases."""
        viewbox = (0, 0, 1, 1)
        padded, width_attribs = layout.pad_and_scale(viewbox, "1in", "4in")
        assert padded == (-0.25, -0.25, 1.5, 1.5)
        assert width_attribs == {"width": "6in", "height": "6in"}

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

    def test_pad_is_constant(self):
        """Pad does not change with scale."""
        viewbox = (0, 0, 10, 20)
        padded, width_attribs = layout.pad_and_scale(viewbox, "1in", "10in")
        assert padded == (-1.0, -1.0, 12.0, 22.0)
        assert width_attribs == {"width": "12in", "height": "22in"}

        padded, width_attribs = layout.pad_and_scale(viewbox, "1in", "100in")
        assert [format_number(x) for x in padded] == ["-.1", "-.1", "10.2", "20.2"]
        assert width_attribs == {"width": "102in", "height": "202in"}

    def test_dpu_(self):
        """dpu_ scales the padded output."""
        viewbox = (0, 0, 10, 20)
        padded, width_attribs = layout.pad_and_scale(viewbox, "1in", "10in")
        assert padded == (-1.0, -1.0, 12.0, 22.0)
        assert width_attribs == {"width": "12in", "height": "22in"}

        padded, width_attribs = layout.pad_and_scale(viewbox, "1in", "10in", dpu=2)
        assert padded == (-1.0, -1.0, 12.0, 22.0)
        assert width_attribs == {"width": "24in", "height": "44in"}

    def test_dpu_scales_without_print_args(self):
        """dpu_ scales output even when no print_width_ or print_height_ are given."""
        viewbox = (0, 0, 1, 1)
        padded, width_attribs = layout.pad_and_scale(viewbox, 1, dpu=2)
        assert padded == (-1, -1, 3, 3)
        assert width_attribs == {"width": "6", "height": "6"}
