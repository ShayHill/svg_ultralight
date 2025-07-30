"""Test methods for BoundElement instances.

:author: Shay Hill
:created: 2025-07-29
"""

from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.constructors import new_element


class TestTransforms:
    """Test methods for BoundElement instances."""

    def test_matrix(self) -> None:
        """Test the transform method."""
        bbox = BoundingBox(0, 0, 100, 100)
        bbox.transform(transformation=(1, 2, 3, 4, 5, 6))
        assert bbox.transformation == (1, 2, 3, 4, 5, 6)

    def test_scale_float(self) -> None:
        """Test the scale method with a float."""
        bbox = BoundingBox(0, 0, 100, 100)
        bbox.transform(scale=2.0)
        assert bbox.transformation == (2.0, 0.0, 0.0, 2.0, 0.0, 0.0)

    def test_scale_int(self) -> None:
        """Test the scale method with an int."""
        bbox = BoundingBox(0, 0, 100, 100)
        bbox.transform(scale=2)
        assert bbox.transformation == (2.0, 0.0, 0.0, 2.0, 0.0, 0.0)


class TestSetScale:
    """Test methods for BoundElement instances."""

    def test_sets_not_transforms(self) -> None:
        """The new scale is the new scale, regardless of the old scale."""
        bbox = BoundingBox(0, 0, 100, 100)
        bbox.scale = (2, 2)
        assert bbox.scale == (2.0, 2.0)
        bbox.scale = (3, 3)
        assert bbox.scale == (3.0, 3.0)


class TestBoundElement:
    """Test methods for BoundElement instances."""

    def test_set_scale(self) -> None:
        """Test the set_scale method."""
        elem = new_element("rect", width=100, height=100)
        bbox = BoundingBox(0, 0, 100, 100)
        blem = BoundElement(elem, bbox)
        blem.scale = (2, 2)
        assert blem.scale == (2.0, 2.0)

    def test_transform(self) -> None:
        """Test the transform method."""
        elem = new_element("rect", width=100, height=100)
        bbox = BoundingBox(0, 0, 100, 100)
        blem = BoundElement(elem, bbox)
        blem.transform(scale=5)
        assert blem.scale == (5.0, 5.0)


class TestPaddedText:
    """Text that padded text instances scale like bound elements."""

    def test_set_scale(self) -> None:
        """Test the set_scale method."""
        elem = new_element("rect", width=100, height=100)
        bbox = BoundingBox(0, 0, 100, 100)
        blem = PaddedText(elem, bbox, 1, 2, 3, 4)
        blem.scale = (2, 2)
        assert blem.scale == (2.0, 2.0)

    def test_transform(self) -> None:
        """Test the transform method."""
        elem = new_element("rect", width=100, height=100)
        bbox = BoundingBox(0, 0, 100, 100)
        blem = PaddedText(elem, bbox, 1, 2, 3, 4)
        blem.transform(scale=5)
        assert blem.scale == (5.0, 5.0)
