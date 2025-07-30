"""Test methods for BoundElement instances.

:author: Shay Hill
:created: 2025-07-29
"""

from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox

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



