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
