import math

from svg_ultralight import layout
from svg_ultralight.unit_conversion import Measurement, UnitOfMeasurement


class TestMeasurement:
    def test_identify_inches(self):
        assert Measurement("1in").value == 96
        assert Measurement("1in").native_unit == UnitOfMeasurement.INCHES

    def test_identify_centimeters(self):
        assert math.isclose(Measurement("1cm").value, 96 / 2.54)
        assert Measurement("1cm").native_unit == UnitOfMeasurement.CENTIMETERS

    def test_identify_millimeters(self):
        assert math.isclose(Measurement("1mm").value, 96 / 25.4)
        assert Measurement("1mm").native_unit == UnitOfMeasurement.MILLIMETERS

    def test_identify_user_units_from_float(self):
        assert Measurement(1).value == 1
        assert Measurement(1).native_unit == UnitOfMeasurement.USER_UNITS

    def test_identify_user_units_from_string(self):
        assert Measurement("1").value == 1
        assert Measurement("1").native_unit == UnitOfMeasurement.USER_UNITS

    def test_set_value(self):
        dim = Measurement("1in")
        dim.set_value(1)
        assert dim.native == "0.010417in"

    def test_get_native(self):
        for dim in ("1in", "1cm", "1mm", "1"):
            assert Measurement(dim).native == dim

    def test_get_inches(self):
        assert Measurement("1in").inches == "1in"

    def test_get_centimeters(self):
        assert Measurement("1cm").centimeters == "1cm"

    def test_get_millimeters(self):
        assert Measurement("1mm").millimeters == "1mm"


class TestLayout:
    def test_standard(self):
        """No print dimensions give expanded pad argument
        and no width args"""
        pad, width_attribs = layout.pad_and_scale(3, 4, 5, 0, 0)
        assert pad == (5, 5, 5, 5)
        assert width_attribs == {}

    def test_string_padding(self):
        """Test that string padding is converted to float"""
        pad, width_attribs = layout.pad_and_scale(3, 4, "1in", 0, 0)
        assert pad == (96, 96, 96, 96)
        assert width_attribs == {}

    def test_print_width(self):
        """Test that print width is used to calculate pad"""
        pad, width_attribs = layout.pad_and_scale(96, 4, "0.25in", "2in", 0)
        assert pad == (12, 12, 12, 12)
        assert width_attribs == {"width": "2.5in"}

    def test_print_height(self):
        """Test that print width is used to calculate pad"""
        pad, width_attribs = layout.pad_and_scale(3, 96, "0.25in", 0, "2in")
        assert pad == (12, 12, 12, 12)
        assert width_attribs == {"height": "2.5in"}

    def test_width_wins(self):
        """The tighter fit (width or height) should be used"""
        pad, width_attribs = layout.pad_and_scale(3, 4, 0, 2, 200)
        assert pad == (0, 0, 0, 0)
        assert width_attribs == {"width": "2"}

    def test_height_wins(self):
        """The tighter fit (width or height) should be used"""
        pad, width_attribs = layout.pad_and_scale(3, 4, 0, 200, 2)
        assert pad == (0, 0, 0, 0)
        assert width_attribs == {"height": "2"}

    def test_padding_scale(self):
        """Test that padding is scaled"""
        pad, width_attribs = layout.pad_and_scale(1, 1, 1, 5, None)

        assert pad == (0.2, 0.2, 0.2, 0.2)
        assert width_attribs == {"width": "7"}
