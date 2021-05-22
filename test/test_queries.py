#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
""" Test queries on a temporary file

:author: Shay Hill
:created: 7/25/2020

A quick test. Won't be able to run it till you change INKSCAPE to the correct path on
your system.
"""

import math

from svg_ultralight import new_svg_root
from svg_ultralight.constructors import new_element, new_sub_element
from svg_ultralight.query import (
    BoundingBox,
    get_bounding_box,
    map_ids_to_bounding_boxes,
)

INKSCAPE = r"C:\Program Files\Inkscape\bin\inkscape"


aaa = BoundingBox(-2, -4, 10, 20)
bbb = BoundingBox(3, 4, 10, 20)


class TestTransformBoundingBoxes:
    def test_transforms_commutative(self):
        """
        Scale then transform = transform then scale
        """
        bbox_a = BoundingBox(-20000, -4, 10, 30)
        bbox_b = BoundingBox(-20000, -4, 10, 30)

        bbox_a.width = 100
        bbox_a.x = 200

        bbox_b.x = 200
        bbox_b.width = 100

        assert bbox_a.transform_string == bbox_b.transform_string


class TestMapIdsToBoundingBoxes:
    def test_gets_bboxes(self) -> None:
        """
        Run with a temporary file.
        """
        expected = {
            "svg4": BoundingBox(x=0.0, y=0.0, width=16.0, height=32.0),
            "rect1": BoundingBox(x=0.0, y=0.0, width=16.0, height=9.0),
            "rect2": BoundingBox(x=0.0, y=0.0, width=8.0, height=32.0),
        }

        xml = new_svg_root(10, 20, 160, 19, id="svg1")
        new_sub_element(xml, "rect", id="rect1", x=0, y=0, width=16, height=9)
        new_sub_element(xml, "rect", id="rect2", x=0, y=0, width=8, height=32)
        result = map_ids_to_bounding_boxes(INKSCAPE, xml)
        assert result == expected


class TestGetBBox:
    def test_single(self) -> None:
        """
        Return bounding box around entire group.
        :return:
        """
        rect = new_element("rect", id="rect1", x=0, y=0, width=16, height=9)
        result = get_bounding_box(INKSCAPE, rect)
        assert result == BoundingBox(0, 0, 16, 9)

    def test_grouped(self) -> None:
        """
        Return bounding box around entire group.
        :return:
        """
        xml = new_svg_root(10, 20, 160, 19, id="svg1")
        group = new_sub_element(xml, "g", id="grouped elements")
        new_sub_element(group, "rect", id="rect1", x=0, y=0, width=16, height=9)
        new_sub_element(group, "rect", id="rect2", x=1, y=1, width=8, height=32)
        result = get_bounding_box(INKSCAPE, group)
        assert result == BoundingBox(0, 0, 16, 33)


class TestAlterBoundingBox:
    def test_reverse_width(self) -> None:
        """ adjust width one way then the other returns to original box """
        bbox = BoundingBox(10, 20, 30, 40)
        bbox.x = 100
        bbox.y = 200
        bbox.height = 200
        bbox.height = 40
        assert math.isclose(bbox._scale, 1)
        assert math.isclose(bbox._translation_x, 90)
        assert math.isclose(bbox._translation_y, 180)
