"""Test bounding classes and functions not tested elsewhere.

:author: Shay Hill
:created: 2024-05-05
"""

import pytest
import math
from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
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