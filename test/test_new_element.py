#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
"""Test functions in constructors.new_element

:author: Shay Hill
:created: 1/31/2020
"""

from new_element import new_element, new_sub_element, update_element, deepcopy_element
from lxml import etree  # type: ignore


class TestNewElement:
    def test_params(self) -> None:
        """Replace _ with -. Pass params.values() as strings"""
        elem = new_element("line", x=10, y1=80, stroke_width="2")
        assert etree.tostring(elem) == b'<line x="10" y1="80" stroke-width="2"/>'

    def test_trailing_underscore(self) -> None:
        """Remove trailing _ from params"""
        elem = new_element("line", x=10, y1=80, in_="SourceAlpha")
        assert etree.tostring(elem) == b'<line x="10" y1="80" in="SourceAlpha"/>'

    def test_param_text(self) -> None:
        """Insert text between tags with parameters"""
        elem = new_element("text", x=120, y=12, text="text here")
        assert etree.tostring(elem) == b'<text x="120" y="12">text here</text>'

    def test_text(self) -> None:
        """Insert text between tags"""
        elem = new_element("text", text="text here")
        assert etree.tostring(elem) == b"<text>text here</text>"


class TestNewSubElement:
    def test_sub_element(self) -> None:
        """New element is a sub-element of parent"""
        parent = new_element("g")
        _ = new_sub_element(parent, "rect")
        assert etree.tostring(parent) == b"<g><rect/></g>"


class TestUpdateElement:
    def test_new_params(self) -> None:
        """New params added"""
        elem = new_element("line", x=10, y1=80)
        update_element(elem, stroke_width=2)
        assert etree.tostring(elem) == b'<line x="10" y1="80" stroke-width="2"/>'


class TestDeepcopyElement:
    def test_is_copy(self) -> None:
        """"""
        group = new_element("g")
        line = new_sub_element(group, "line", x=10, y1=80)
        group_copy = deepcopy_element(group, stroke="black")
        assert (
            etree.tostring(group_copy)
            == b'<g stroke="black"><line x="10" y1="80"/></g>'
        )
        assert line in group
        assert line not in group_copy
