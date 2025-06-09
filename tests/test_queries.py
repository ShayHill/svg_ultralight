"""Test queries on a temporary file.

:author: Shay Hill
:created: 7/25/2020

A quick test. Won't be able to run it till you change INKSCAPE to the correct path on
your system.
"""

from dataclasses import dataclass
from pathlib import Path

import pytest

from svg_ultralight import BoundingBox, new_svg_root
from svg_ultralight.constructors.new_element import new_element
from svg_ultralight.constructors import new_sub_element
from svg_ultralight.query import map_elems_to_bounding_boxes, get_bounding_boxes, get_bounding_box

INKSCAPE = Path(r"C:\Program Files\Inkscape\bin\inkscape")

if not INKSCAPE.with_suffix(".exe").exists():
    msg = "Inkscape not found. Please install Inkscape or update the INKSCAPE path var."
    raise FileNotFoundError(msg)


class TestMergeBoundingBoxes:
    def test_new_merged_bbox(self):
        bbox_a = BoundingBox(-2, -4, 10, 20)
        bbox_b = BoundingBox(0, 0, 10, 10)
        merged = BoundingBox.merged(bbox_a, bbox_b)
        assert merged.x == -2
        assert merged.y == -4
        assert merged.width == 12
        assert merged.height == 20


@dataclass
class MockSupportsBounds:
    x: float
    y: float
    width: float
    height: float


class TestBoundingBox:
    @pytest.fixture
    def bounding_box(self):
        return BoundingBox(0, 0, 100, 200)

    def test_scale(self):
        bbox = BoundingBox(100, 200, 300, 400)
        assert bbox.scale == (1.0, 1.0)
        bbox.scale = (3.0, 3.0)
        bbox.x = 750
        bbox.scale = (2.0, 2.0)
        assert bbox.scale == (2.0, 2.0)
        assert bbox.x == 500
        assert bbox.y == 400
        assert bbox.width == 600.0
        assert bbox.height == 800.0

    def test_alter_scale(self):
        bbox = BoundingBox(100, 200, 300, 400)
        assert bbox.scale == (1.0, 1.0)
        bbox.scale = (3.0, 3.0)
        bbox.transform(scale=(10.0, 10.0))
        assert bbox.scale == (30.0, 30.0)
        assert bbox.x == 3000
        assert bbox.y == 6000
        assert bbox.width == 9000.0
        assert bbox.height == 12000.0

    def test_x(self, bounding_box: BoundingBox):
        assert bounding_box.x == 0.0
        bounding_box.x = 50.0
        assert bounding_box.x == 50.0
        assert bounding_box.cx == 100.0

    def test_x2(self, bounding_box: BoundingBox):
        assert bounding_box.x2 == 100.0
        bounding_box.x2 = 150.0
        assert bounding_box.x2 == 150.0
        assert bounding_box.cx == 100.0

    def test_y(self, bounding_box: BoundingBox):
        assert bounding_box.y == 0.0
        bounding_box.y = 50.0
        assert bounding_box.y == 50.0
        assert bounding_box.cy == 150.0

    def test_y2(self, bounding_box: BoundingBox):
        assert bounding_box.y2 == 200.0
        bounding_box.y2 = 250.0
        assert bounding_box.y2 == 250.0
        assert bounding_box.cy == 150.0

    def test_width(self, bounding_box: BoundingBox):
        assert bounding_box.width == 100.0
        bounding_box.width = 150.0
        assert bounding_box.width == 150.0
        assert bounding_box.x2 == 150.0

    def test_height(self, bounding_box: BoundingBox):
        assert bounding_box.height == 200.0
        bounding_box.height = 250.0
        assert bounding_box.height == 250.0
        assert bounding_box.y2 == 250.0

    def test_transform_string(self, bounding_box: BoundingBox):
        transform_string = bounding_box.transform_string
        assert transform_string == "matrix(1 0 0 1 0 0)"

    def test_merge(self):
        bbox1 = MockSupportsBounds(0, 0, 100, 200)
        bbox2 = MockSupportsBounds(50, 50, 150, 250)
        merged_bbox = BoundingBox.merged(bbox1, bbox2)
        assert merged_bbox.x == 0.0
        assert merged_bbox.y == 0.0
        assert merged_bbox.width == 200.0
        assert merged_bbox.height == 300.0


class TestTransformBoundingBoxes:
    def test_transforms_commutative(self):
        """Scale then transform = transform then scale."""
        bbox_a = BoundingBox(-20000, -4, 10, 30)
        bbox_b = BoundingBox(-20000, -4, 10, 30)

        bbox_a.width = 100
        bbox_a.x = 200

        bbox_b.x = 200
        bbox_b.width = 100

        assert bbox_a.transform_string == bbox_b.transform_string

    def test_width_does_not_alter_x(self):
        """Setting width does not change x."""
        bbox = BoundingBox(-20000, -4, 10, 30)
        bbox_x = bbox.x
        bbox.width = 100
        assert bbox.x == bbox_x

    def test_width_does_not_alter_y(self):
        """Setting width does not change x."""
        bbox = BoundingBox(-20000, -4, 10, 30)
        bbox_x = bbox.x
        bbox.width = 100
        assert bbox.x == bbox_x


class TestMapElemsToBoundingBoxes:
    def test_gets_bboxes(self) -> None:
        """Run with a temporary file."""
        xml = new_svg_root(10, 20, 160, 19, id="svg1")
        rect1 = new_sub_element(xml, "rect", id="rect1", x=0, y=0, width=16, height=9)
        rect2 = new_sub_element(xml, "rect", id="rect2", x=0, y=0, width=8, height=32)
        result = map_elems_to_bounding_boxes(INKSCAPE, xml)
        assert result[rect1] == BoundingBox(0.0, 0.0, 16.0, 9.0)
        assert result[rect2] == BoundingBox(0.0, 0.0, 8.0, 32.0)

    def test_removes_temp_ids(self) -> None:
        """Removes temporary IDs created during bounding box mapping."""
        xml = new_svg_root(10, 20, 160, 19, id="svg1")
        rect1 = new_sub_element(xml, "rect", x=0, y=0, width=16, height=9)
        rect2 = new_sub_element(xml, "rect", x=0, y=0, width=8, height=32)
        rect3 = new_sub_element(xml, "rect", x=0, y=0, width=12, height=18)
        result = map_elems_to_bounding_boxes(INKSCAPE, xml)
        for elem in (xml, rect1, rect2, rect3):
            assert elem in result
        assert xml.attrib.get("id") == "svg1"
        for elem in (rect1, rect2, rect3):
            assert "id" not in elem.attrib

    def test_get_bboxes_explicit(self) -> None:
        """Returns a dict with an entry for each element plus an envelope entry."""
        xml = new_svg_root(10, 20, 160, 19, id="svg1")
        rect1 = new_sub_element(xml, "rect", x=0, y=0, width=16, height=9)
        rect2 = new_sub_element(xml, "rect", x=0, y=0, width=8, height=32)
        rect3 = new_sub_element(xml, "rect", x=0, y=0, width=12, height=18)
        rect4 = new_sub_element(xml, "rect", x=0, y=0, width=12, height=18)

        result = get_bounding_boxes(INKSCAPE, xml, rect1, rect2, rect3, rect4)
        assert result[0] == BoundingBox(
            x=0.0,
            y=0.0,
            width=16.0,
            height=32.0,
            transformation=(1, 0, 0, 1, 0, 0),
        )
        assert result[1] == BoundingBox(
            x=0.0, y=0.0, width=16.0, height=9.0, transformation=(1, 0, 0, 1, 0, 0)
        )
        assert result[2] == BoundingBox(
            x=0.0, y=0.0, width=8.0, height=32.0, transformation=(1, 0, 0, 1, 0, 0)
        )
        assert result[3] == BoundingBox(
            x=0.0,
            y=0.0,
            width=12.0,
            height=18.0,
            transformation=(1, 0, 0, 1, 0, 0),
        )
        assert result[4] == BoundingBox(
            x=0.0,
            y=0.0,
            width=12.0,
            height=18.0,
            transformation=(1, 0, 0, 1, 0, 0),
        )

    def test_get_bbox_vs_boxes(self) -> None:
        """Multiple calls to get_bounding_box are equivalent to a single call."""
        xml = new_svg_root(10, 20, 160, 19, id="svg1")
        rect1 = new_sub_element(xml, "rect", x=0, y=0, width=16, height=9)
        rect2 = new_sub_element(xml, "rect", x=0, y=0, width=8, height=32)
        rect3 = new_sub_element(xml, "rect", x=0, y=0, width=12, height=18)
        rect4 = new_sub_element(xml, "rect", x=0, y=0, width=12, height=18)
        elems = (xml, rect1, rect2, rect3, rect4)
        result = get_bounding_boxes(INKSCAPE, *elems)
        assert result == tuple(get_bounding_box(INKSCAPE, e) for e in elems)

class TestAlterBoundingBox:
    def test_reverse_width(self) -> None:
        """adjust width one way then the other returns to original box."""
        bbox = BoundingBox(10, 20, 30, 40)
        bbox.x = 100
        bbox.y = 200
        bbox.height = 200
        bbox.height = 40
        assert bbox.transformation == (1, 0, 0, 1, 90, 180)




