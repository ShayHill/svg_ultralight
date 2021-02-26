#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
""" Test queries on a temporary file

:author: Shay Hill
:created: 7/25/2020

A quick test. Won't be able to run it till you change INKSCAPE to the correct path on
your system.
"""

from svg_ultralight import new_svg_root
from svg_ultralight.constructors import new_sub_element, new_element
from svg_ultralight.query import (
    BoundingBox,
    map_ids_to_bounding_boxes,
    get_bounding_box,
)

INKSCAPE = "C:\\Program Files\\Inkscape\\inkscape"


class TestMapIdsToBoundingBoxes:
    def test_gets_bboxes(self) -> None:
        """
        Run with a temporary file.
        """
        expected = {
            "svg4": BoundingBox(
                origin_x=0.0,
                origin_y=0.0,
                origin_width=16.0,
                origin_height=32.0,
                scale=1,
                translation_x=0,
                translation_y=0,
            ),
            "rect1": BoundingBox(
                origin_x=0.0,
                origin_y=0.0,
                origin_width=16.0,
                origin_height=9.0,
                scale=1,
                translation_x=0,
                translation_y=0,
            ),
            "rect2": BoundingBox(
                origin_x=0.0,
                origin_y=0.0,
                origin_width=8.0,
                origin_height=32.0,
                scale=1,
                translation_x=0,
                translation_y=0,
            ),
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
