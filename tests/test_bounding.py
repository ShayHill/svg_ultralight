"""Test bounding classes and functions not tested elsewhere.

:author: Shay Hill
:created: 2024-05-05
"""

import pytest
import math
from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.bounding_boxes.type_bound_collection import BoundCollection
from svg_ultralight.bounding_boxes.bound_helpers import (
    pad_bbox,
    cut_bbox,
    bbox_dict,
    new_bbox_rect,
    _expand_pad,
)
import copy
from svg_ultralight.constructors import new_element


class TestBoundElement:
    @pytest.fixture
    def bound_element(self) -> BoundElement:
        elem = new_element("rect", x=0, y=0, width=100, height=200)
        bbox = BoundingBox(0, 0, 100, 200)
        return BoundElement(elem, bbox)

    def test_scale(self):
        elem = new_element("rect", x=100, y=200, width=300, height=400)
        bbox = BoundingBox(100, 200, 300, 400)
        blem = BoundElement(elem, bbox)
        assert blem.scale == 1.0
        blem.scale = 3.0
        blem.x = 750
        blem.scale = 2.0
        assert blem.scale == 2.0
        assert blem.x == 500
        assert blem.y == 400
        assert blem.width == 600.0
        assert blem.height == 800.0

    def test_alter_scale(self):
        elem = new_element("rect", x=100, y=200, width=300, height=400)
        bbox = BoundingBox(100, 200, 300, 400)
        blem = BoundElement(elem, bbox)
        assert blem.scale == 1.0
        blem.scale = 3.0
        blem.scale *= 10.0
        assert blem.scale == 30.0
        assert blem.x == 3000
        assert blem.y == 6000
        assert blem.width == 9000.0
        assert blem.height == 12000.0

    def test_x(self, bound_element: BoundElement):
        assert bound_element.x == 0.0
        bound_element.x = 50.0
        assert bound_element.x == 50.0
        assert bound_element.cx == 100.0

    def test_x2(self, bound_element: BoundElement):
        assert bound_element.x2 == 100.0
        bound_element.x2 = 150.0
        assert bound_element.x2 == 150.0
        assert bound_element.cx == 100.0

    def test_y(self, bound_element: BoundElement):
        assert bound_element.y == 0.0
        bound_element.y = 50.0
        assert bound_element.y == 50.0
        assert bound_element.cy == 150.0

    def test_y2(self, bound_element: BoundElement):
        assert bound_element.y2 == 200.0
        bound_element.y2 = 250.0
        assert bound_element.y2 == 250.0
        assert bound_element.cy == 150.0

    def test_width(self, bound_element: BoundElement):
        assert bound_element.width == 100.0
        bound_element.width = 150.0
        assert bound_element.width == 150.0
        assert bound_element.x2 == 150.0

    def test_height(self, bound_element: BoundElement):
        assert bound_element.height == 200.0
        bound_element.height = 250.0
        assert bound_element.height == 250.0
        assert bound_element.y2 == 250.0


class TestPaddedText:
    @pytest.fixture
    def bound_element(self) -> PaddedText:
        elem = new_element("rect", x=0, y=0, width=100, height=200)
        bbox = BoundingBox(0, 0, 100, 200)
        return PaddedText(elem, bbox, 1, 2, 3, 4)

    def test_scale(self):
        elem = new_element("rect", x=100, y=200, width=300, height=400)
        bbox = BoundingBox(100, 200, 300, 400)
        blem = BoundElement(elem, bbox)
        assert blem.scale == 1.0
        blem.scale = 3.0
        blem.x = 750
        blem.scale = 2.0
        assert blem.scale == 2.0
        assert blem.x == 500
        assert blem.y == 400
        assert blem.width == 600.0
        assert blem.height == 800.0

    def test_alter_scale(self):
        elem = new_element("rect", x=100, y=200, width=300, height=400)
        bbox = BoundingBox(100, 200, 300, 400)
        blem = BoundElement(elem, bbox)
        assert blem.scale == 1.0
        blem.scale = 3.0
        blem.scale *= 10.0
        assert blem.scale == 30.0
        assert blem.x == 3000
        assert blem.y == 6000
        assert blem.width == 9000.0
        assert blem.height == 12000.0

    def test_x(self, bound_element: BoundElement):
        assert bound_element.x == -4
        bound_element.x = 50.0
        assert bound_element.x == 50.0
        assert bound_element.cx == 103.0

    def test_x2(self, bound_element: BoundElement):
        assert bound_element.x2 == 102
        bound_element.x2 = 150.0
        assert bound_element.x2 == 150.0
        assert bound_element.cx == 97.0

    def test_y(self, bound_element: BoundElement):
        assert bound_element.y == -1
        bound_element.y = 50.0
        assert bound_element.y == 50.0
        assert bound_element.cy == 152.0

    def test_y2(self, bound_element: BoundElement):
        assert bound_element.y2 == 203.0
        bound_element.y2 = 250.0
        assert bound_element.y2 == 250.0
        assert bound_element.cy == 148.0

    def test_width(self, bound_element: BoundElement):
        assert bound_element.width == 106.0
        bound_element.width = 150.0
        assert bound_element.width == 150.0
        assert bound_element.x2 == 146.0

    def test_height(self, bound_element: BoundElement):
        assert bound_element.height == 204.0
        bound_element.height = 250.0
        assert math.isclose(bound_element.height, 252.76)
        assert bound_element.y2 == 203.0


class TestBoundCollection:

    @pytest.fixture
    def bound_collection(self) -> BoundCollection:
        elem = new_element("rect", x=0, y=0, width=100, height=200)
        bbox = BoundingBox(0, 0, 100, 200)
        blem = PaddedText(elem, bbox, 1, 2, 3, 4)
        return BoundCollection(blem, copy.deepcopy(elem))

    def test_blem_and_elem(self):
        """Test that bound element and unbound element transforms are the same."""
        rect = new_element("rect", x=0, y=0, width=100, height=200)
        bbox = BoundingBox(0, 0, 100, 200)
        blem = BoundElement(rect, bbox)
        elem = copy.deepcopy(rect)
        bound_collection = BoundCollection(blem, elem)
        bound_collection.x = -4
        bound_collection.scale = 10
        bound_collection.width = 60
        bound_collection.cy = -40
        blem_trans = blem.elem.attrib["transform"]
        elem_trans = elem.attrib["transform"]
        assert blem_trans == elem_trans


class TestBoundHelpers:
    def test_pad_bbox(self):
        bbox = BoundingBox(0, 0, 4, 4)
        padded = pad_bbox(bbox, 1)
        assert padded.x == -1
        assert padded.y == -1
        assert padded.width == 6
        assert padded.height == 6

    def test_pad_bbox_t1(self):
        bbox = BoundingBox(0, 0, 4, 4)
        padded = pad_bbox(bbox, (1,))
        assert padded.x == -1
        assert padded.y == -1
        assert padded.width == 6
        assert padded.height == 6

    def test_pad_bbox_t2(self):
        bbox = BoundingBox(0, 0, 4, 4)
        padded = pad_bbox(bbox, (1, 2))
        assert padded.x == -2
        assert padded.y == -1
        assert padded.width == 8
        assert padded.height == 6

    def test_pad_bbox_t3(self):
        bbox = BoundingBox(0, 0, 4, 4)
        padded = pad_bbox(bbox, (1, 2, 3))
        assert padded.x == -2
        assert padded.y == -1
        assert padded.width == 8
        assert padded.height == 8

    def test_pad_bbox_t4(self):
        bbox = BoundingBox(0, 0, 4, 4)
        padded = pad_bbox(bbox, (1, 2, 3, 4))
        assert padded.x == -4
        assert padded.y == -1
        assert padded.width == 10
        assert padded.height == 8

    def test_cut_bbox(self):
        bbox = BoundingBox(0, 0, 4, 4)
        cut = cut_bbox(bbox, x=1)
        assert cut.x == 1
        assert cut.y == 0
        assert cut.width == 3
        assert cut.height == 4

    def test_bbox_dict(self):
        bbox = BoundingBox(0, 1, 2, 3)
        assert bbox_dict(bbox) == {"x": 0, "y": 1, "width": 2, "height": 3}

    def test_new_bbox_rect(self):
        bbox = BoundingBox(0, 1, 2, 3)
        elem = new_bbox_rect(bbox)
        assert elem.attrib == {"x": "0", "y": "1", "width": "2", "height": "3"}

