"""Test functions in root_elements.py.

:author: Shay Hill
:created: 2023-09-24
"""

import pytest
from lxml.etree import _Element as EtreeElement  # pyright: ignore[reportPrivateUsage]

from svg_ultralight.bounding_boxes.bound_helpers import new_bound_union
from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.constructors import new_element
from svg_ultralight.root_elements import new_svg_root_around_bounds


class TestNewSvgRootAroundBounds:
    def test_empty(self):
        """Raise ValueError if no bounding boxes found."""
        with pytest.raises(ValueError, match="At least one argument"):
            _ = new_svg_root_around_bounds()

    def test_no_bound_elements(self):
        """Raise ValueError if no BoundElements found."""
        with pytest.raises(ValueError, match="At least one argument"):
            _ = new_svg_root_around_bounds(new_element("g"))

    def test_bounding_boxes(self):
        """Create svg root element from bounding boxes."""
        bboxes = [BoundingBox(0, 0, 100, 100), BoundingBox(50, 50, 150, 150)]
        result = new_svg_root_around_bounds(*bboxes)
        assert isinstance(result, EtreeElement)
        assert result.attrib["viewBox"] == "0 0 200 200"

    def test_bound_elements(self):
        """Create svg root element from BoundElements."""
        bboxes = [BoundingBox(0, 0, 100, 100), BoundingBox(50, 50, 150, 150)]
        args = bboxes[0], BoundElement(new_element("g"), bboxes[1])
        result = new_svg_root_around_bounds(*args)
        assert isinstance(result, EtreeElement)
        assert result.attrib["viewBox"] == "0 0 200 200"

    def test_padded_text(self):
        """Create svg root element from BoundElements."""
        bboxes = [BoundingBox(0, 0, 100, 100), BoundingBox(50, 50, 150, 150)]
        args = bboxes[0], PaddedText(new_element("g"), bboxes[1], 1, 1, 1, 1)
        result = new_svg_root_around_bounds(*args)
        assert isinstance(result, EtreeElement)
        assert result.attrib["viewBox"] == "0 0 201 201"


class TestNewBoundUnion:
    def test_bounding_boxes_only(self):
        """Raise an error if no elements found."""
        bboxes = [BoundingBox(0, 0, 100, 100), BoundingBox(50, 50, 150, 150)]
        union = new_bound_union(*bboxes)
        assert len(union.elem) == 0
        assert union.elem.tag == "g"

    def test_elements_only(self):
        """Raise an error if no elements found."""
        elems = [new_element("g"), new_element("g")]
        with pytest.raises(ValueError, match="must be a BoundElement, BoundingBox"):
            _ = new_bound_union(*elems)

    def test_bound_elements(self):
        """Create svg root element from BoundElements."""
        bboxes = [BoundingBox(0, 0, 100, 100), BoundingBox(50, 50, 150, 150)]
        args = bboxes[0], BoundElement(new_element("g"), bboxes[1])
        result = new_bound_union(*args)
        assert isinstance(result, BoundElement)

    def test_padded_text(self):
        """Create svg root element from BoundElements."""
        bboxes = [BoundingBox(0, 0, 100, 100), BoundingBox(50, 50, 150, 150)]
        args = bboxes[0], PaddedText(new_element("g"), bboxes[1], 1, 1, 1, 1)
        result = new_bound_union(*args)
        assert isinstance(result, BoundElement)
