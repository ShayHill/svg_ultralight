#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
""" Test queries on a temporary file

:author: Shay Hill
:created: 7/25/2020

A quick test. Won't be able to run it till you change INKSCAPE to the correct path on
your system.
"""

import math
import pytest

from svg_ultralight import new_svg_root
from svg_ultralight.constructors import new_sub_element
from svg_ultralight.query import (
    BoundingBox,
    get_bounding_box,
    map_ids_to_bounding_boxes,
)

INKSCAPE = r"C:\Program Files\Inkscape\bin\inkscape"


class TestMergeBoundingBoxes:
    def test_merge_deprecation_warning(self):
        bbox_a = BoundingBox(-2, -4, 10, 20)
        bbox_b = BoundingBox(0, 0, 10, 10)
        with pytest.raises(DeprecationWarning):
            _ = bbox_a.merge(bbox_b)

    def test_new_merged_bbox(self):
        bbox_a = BoundingBox(-2, -4, 10, 20)
        bbox_b = BoundingBox(0, 0, 10, 10)
        merged = BoundingBox.merged(bbox_a, bbox_b)
        assert merged.x == -2
        assert merged.y == -4
        assert merged.width == 12
        assert merged.height == 20


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
        xml = new_svg_root(10, 20, 160, 19, id="svg1")
        _ = new_sub_element(xml, "rect", id="rect1", x=0, y=0, width=16, height=9)
        _ = new_sub_element(xml, "rect", id="rect2", x=0, y=0, width=8, height=32)
        result = map_ids_to_bounding_boxes(INKSCAPE, xml)
        assert result["rect1"] == BoundingBox(0.0, 0.0, 16.0, 9.0)
        assert result["rect2"] == BoundingBox(0.0, 0.0, 8.0, 32.0)

    def test_adds_missing_ids(self) -> None:
        """Returns a dict with an entry for each element plus an envelope entry."""
        xml = new_svg_root(10, 20, 160, 19, id="svg1")
        rect1 = new_sub_element(xml, "rect", x=0, y=0, width=16, height=9)
        rect2 = new_sub_element(xml, "rect", x=0, y=0, width=8, height=32)
        rect3 = new_sub_element(xml, "rect", x=0, y=0, width=12, height=18)
        result = map_ids_to_bounding_boxes(INKSCAPE, xml)
        assert xml.get("id") in result.keys()
        assert rect1.get("id") in result.keys()
        assert rect2.get("id") in result.keys()
        assert rect3.get("id") in result.keys()


class TestGetBBox:
    def test_raises_deprecation_warning(self) -> None:
        """
        Return bounding box around entire group.
        :return:
        """
        xml = new_svg_root(10, 20, 160, 19, id="svg1")
        group = new_sub_element(xml, "g", id="grouped elements")
        _ = new_sub_element(group, "rect", id="rect1", x=0, y=0, width=16, height=9)
        _ = new_sub_element(group, "rect", id="rect2", x=1, y=1, width=8, height=32)
        with pytest.raises(DeprecationWarning):
            _ = get_bounding_box(INKSCAPE, group)


class TestAlterBoundingBox:
    def test_reverse_width(self) -> None:
        """adjust width one way then the other returns to original box"""
        bbox = BoundingBox(10, 20, 30, 40)
        bbox.x = 100
        bbox.y = 200
        bbox.height = 200
        bbox.height = 40
        assert math.isclose(bbox.scale, 1)
        assert math.isclose(bbox._translation_x, 90)  # type: ignore
        assert math.isclose(bbox._translation_y, 180)  # type: ignore
