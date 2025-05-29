"""Test all documented pad_ argument behavior.

:author: Shay Hill
:created: 2025-05-28
"""

from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.root_elements import new_svg_root, new_svg_root_around_bounds


class TestNumPadArguments:
    """Test that 1, 2, 3, and 4 pad arguments work as in css."""

    def test_new_svg_root_pad_1(self):
        """Given one pad_ argument, pad all sides equally."""
        root = new_svg_root(x_=0, y_=0, width_=100, height_=100, pad_=5)
        assert root.attrib["viewBox"] == "-5 -5 110 110"

    def test_new_svg_root_around_bounds_pad_1(self):
        """Given one pad_ argument, pad all sides equally."""
        bbox = BoundingBox(0, 0, 100, 100)
        root = new_svg_root_around_bounds(bbox, pad_=5)
        assert root.attrib["viewBox"] == "-5 -5 110 110"

    def test_new_svg_root_pad_2(self):
        """Given two pad_ arguments, pad top/bottom and left/right."""
        root = new_svg_root(x_=0, y_=0, width_=100, height_=100, pad_=(5, 10))
        assert root.attrib["viewBox"] == "-10 -5 120 110"

    def test_new_svg_root_around_bounds_pad_2(self):
        """Given two pad_ arguments, pad top/bottom and left/right."""
        bbox = BoundingBox(0, 0, 100, 100)
        root = new_svg_root_around_bounds(bbox, pad_=(5, 10))
        assert root.attrib["viewBox"] == "-10 -5 120 110"

    def test_new_svg_root_pad_3(self):
        """Given three pad_ arguments, pad top, left/right, bottom."""
        root = new_svg_root(x_=0, y_=0, width_=100, height_=100, pad_=(5, 10, 15))
        assert root.attrib["viewBox"] == "-10 -5 120 120"

    def test_new_svg_root_around_bounds_pad_3(self):
        """Given three pad_ arguments, pad top, left/right, bottom."""
        bbox = BoundingBox(0, 0, 100, 100)
        root = new_svg_root_around_bounds(bbox, pad_=(5, 10, 15))
        assert root.attrib["viewBox"] == "-10 -5 120 120"

    def test_new_svg_root_pad_4(self):
        """Given four pad_ arguments, pad top, right, bottom, left."""
        root = new_svg_root(x_=0, y_=0, width_=100, height_=100, pad_=(5, 10, 15, 20))
        assert root.attrib["viewBox"] == "-20 -5 130 120"

    def test_new_svg_root_around_bounds_pad_4(self):
        """Given four pad_ arguments, pad top, right, bottom, left."""
        bbox = BoundingBox(0, 0, 100, 100)
        root = new_svg_root_around_bounds(bbox, pad_=(5, 10, 15, 20))
        assert root.attrib["viewBox"] == "-20 -5 130 120"
