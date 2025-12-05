"""Test function parse_bound_element.

:author: Shay Hill
:created: 2025-10-16
"""

from conftest import TEST_RESOURCES

from svg_ultralight.bounding_boxes.bound_helpers import parse_bound_element

test_svg = TEST_RESOURCES / "arrow.svg"


class TestReadSVG:
    """Test the read_svg module."""

    def test_parse(self):
        """Test get_bounding_box_from_root function."""
        blem = parse_bound_element(test_svg)
        assert blem.bbox.x == 0.0
        assert blem.bbox.y == 0.0
        assert blem.bbox.width == 10.0
        assert blem.bbox.height == 10.0
