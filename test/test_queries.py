#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
""" Test queries on a temporary file

:author: Shay Hill
:created: 7/25/2020

A quick test. Won't be able to run it till you change INKSCAPE to the correct path on
your system.
"""

from svg_ultralight import new_svg_root
from svg_ultralight.constructors import new_sub_element
from svg_ultralight.query import BoundingBox, map_ids_to_bounding_boxes

INKSCAPE = "C:\\Program Files\\Inkscape\\inkscape"


class TestMapIdsToBoundingBoxes:
    def test_gets_bboxes(self) -> None:
        """
        Run with a temporary file.
        """
        expected = {
            "svg1": BoundingBox(x=-10.0, y=-20.0, width=16.0, height=32.0),
            "rect1": BoundingBox(x=-10.0, y=-20.0, width=16.0, height=9.0),
            "rect2": BoundingBox(x=-10.0, y=-20.0, width=8.0, height=32.0),
        }
        xml = new_svg_root(10, 20, 160, 19, id="svg1")
        new_sub_element(xml, "rect", id="rect1", x=0, y=0, width=16, height=9)
        new_sub_element(xml, "rect", id="rect2", x=0, y=0, width=8, height=32)
        result = map_ids_to_bounding_boxes(INKSCAPE, xml=xml)
        assert result == expected
