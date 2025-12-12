"""Test methods for BoundElement instances.

:author: Shay Hill
:created: 2025-07-29
"""

import math
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.constructors import new_element
from svg_ultralight.transformations import (
    mat_dot,
    get_transform_matrix,
    transform_element,
)


class TestTransforms:
    """Test methods for BoundElement instances."""

    def test_matrix(self) -> None:
        """Test the transform method."""
        bbox = BoundingBox(0, 0, 100, 100)
        bbox.transform(transformation=(1, 2, 3, 4, 5, 6))
        assert bbox.transformation == (1, 2, 3, 4, 5, 6)

    def test_reverse(self) -> None:
        mat_a = (1, 2, 3, 4, 5, 6)
        mat_b = (2, 1, 4, 3, 6, 5)
        elem = new_element("circle", cx=0, cy=0, r=1)
        _ = transform_element(elem, mat_a)
        bbox = BoundingBox(0, 0, 1, 1, transformation=mat_a)
        blem = BoundElement(elem, bbox)
        blem.transform(transformation=mat_b, reverse=True)
        assert blem.bbox.transformation == mat_dot(mat_a, mat_b)
        assert get_transform_matrix(blem.elem) == mat_dot(mat_a, mat_b)

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

    def test_vpad_scales(self) -> None:
        """Test that vertical padding scales."""
        elem = new_element("rect", width=100, height=100)
        bbox = BoundingBox(0, 0, 100, 100)
        blem = PaddedText(elem, bbox, 1, 2, 3, 4)

        assert blem.tpad == 1.0
        assert blem.bpad == 3.0

        blem.transform(scale=0.5)
        assert blem.height == 52.0
        assert blem.tpad == 0.5
        assert blem.bpad == 1.5

    def test_vpad_scales_non_uniform(self) -> None:
        """Test that vertical padding scales non-uniformly."""
        elem = new_element("rect", width=100, height=100)
        bbox = BoundingBox(0, 0, 100, 100)
        blem = PaddedText(elem, bbox, 1, 2, 3, 4)

        assert blem.tpad == 1.0
        assert blem.bpad == 3.0

        blem.transform_preserve_sidebearings(scale=(1.5, 0.5))
        assert blem.height == 52.0
        assert blem.width == 156.0
        assert blem.tpad == 0.5
        assert blem.bpad == 1.5

    def test_hpad_does_not_scale(self) -> None:
        """Test that horizontal padding does not scale."""
        elem = new_element("rect", width=100, height=100)
        bbox = BoundingBox(0, 0, 100, 100)
        blem = PaddedText(elem, bbox, 1, 2, 3, 4)

        assert blem.tpad == 1.0
        assert blem.bpad == 3.0

        blem.set_width_preserve_sidebearings(10)
        assert math.isclose(blem.width, 10.0)
        assert blem.rpad == 2.0
        assert blem.lpad == 4.0
