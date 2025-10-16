"""Test function in the read_svg module.

:author: Shay Hill
:created: 2025-10-16
"""

from conftest import TEST_RESOURCES

from svg_ultralight.read_svg import parse

test_svg = TEST_RESOURCES / "arrow.svg"


class TestReadSVG:
    """Test the read_svg module."""

    def test_parse(self):
        """Test get_bounding_box_from_root function."""
        blem = parse(test_svg)
        assert blem.bbox.x == 0.0
        assert blem.bbox.y == 0.0
        assert blem.bbox.width == 10.0
        assert blem.bbox.height == 10.0
