"""Test functions in string_conversion.py.

:author: Shay Hill
:created: 2023-09-23
"""

import svg_ultralight.string_conversion as mod


class TestFormatNuber:
    def test_negative_zero(self):
        """Remove "-" from "-0"."""
        assert mod.format_number(-0.0000000001) == "0"

    def test_round_to_int(self):
        """Round to int if no decimal values !- 0."""
        assert mod.format_number(1.0000000001) == "1"


class TestFormatNumbers:
    def test_empty(self):
        """Return empty list."""
        assert mod.format_numbers([]) == []

    def test_explicit(self):
        """Return list of formatted strings."""
        assert mod.format_numbers([1, 2, 3]) == ["1", "2", "3"]


class TestFormatAttrDict:
    def test_float(self):
        """Return string of float."""
        assert mod.format_attr_dict(x=1.0) == {"x": "1"}

    def test_float_string(self):
        """Return string of float."""
        assert mod.format_attr_dict(x="1.0") == {"x": "1"}

    def test_exponential_float(self):
        """Return string of float."""
        assert mod.format_attr_dict(x="1.0e-10") == {"x": "0"}

    def test_exponential_float_string(self):
        """Return string of float."""
        assert mod.format_attr_dict(x=1.0e-10) == {"x": "0"}

    def test_datastring(self):
        """Find and format floats in a datastring."""
        assert mod.format_attr_dict(d="M1.0,0 Q -0,.33333333 1,2z") == {
            "d": "M1,0 Q 0,0.333333 1,2z"
        }

    def test_datastring_with_exponential_number(self):
        """Find and format floats in a datastring."""
        assert mod.format_attr_dict(d="M1.0,1.0e-10 Q -0,.33333333 1,2z") == {
            "d": "M1,0 Q 0,0.333333 1,2z"
        }

    def test_format_string(self):
        """Format floats in a format SVG attribute string."""
        assert mod.format_attr_dict(
            transform="translate(1.0, -0) scale(1.0, 1.0)"
        ) == {"transform": "translate(1, 0) scale(1, 1)"}

    def test_trailing_underscore(self):
        """Remove trailing underscore from key."""
        assert mod.format_attr_dict(x_=1) == {"x": "1"}

    def test_replace_underscore(self):
        """Replace underscore with hyphen."""
        assert mod.format_attr_dict(x_y=1) == {"x-y": "1"}
