#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
"""Test functions in constructors.new_element

:author: Shay Hill
:created: 1/31/2020
"""

from lxml import etree

from svg_ultralight import constructors


class TestId:
    """Test the id attribute of new_element"""

    def test_id(self):
        """Test that id is set correctly when passed"""
        element = constructors.new_element("g", id="test")
        assert element.get("id") == "test"

    def test_no_id(self):
        """Random ID is generated when not passed"""
        element = constructors.new_element("g")
        assert element.get("id") is not None


class TestNewElement:
    def test_params(self) -> None:
        """Replace _ with -. Pass params.values() as strings"""
        elem = constructors.new_element("line", x=10, y1=80, stroke_width="2")
        del(elem.attrib["id"])
        assert etree.tostring(elem) == b'<line x="10" y1="80" stroke-width="2"/>'

    def test_qualified_name_string_conversion(self) -> None:
        """If a keyword argument has :, convert to qname"""
        elem = constructors.new_element("line", **{"xlink:href": 10})
        del(elem.attrib["id"])
        assert (
            etree.tostring(elem)
            == b'<line xmlns:ns0="http://www.w3.org/1999/xlink" ns0:href="10"/>'
        )

    def test_trailing_underscore(self) -> None:
        """Remove trailing _ from params"""
        elem = constructors.new_element("line", x=10, y1=80, in_="SourceAlpha")
        del(elem.attrib["id"])
        assert etree.tostring(elem) == b'<line x="10" y1="80" in="SourceAlpha"/>'

    def test_param_text(self) -> None:
        """Insert text between tags with parameters"""
        elem = constructors.new_element("text", x=120, y=12, text="text here")
        del(elem.attrib["id"])
        assert etree.tostring(elem) == b'<text x="120" y="12">text here</text>'

    def test_text(self) -> None:
        """Insert text between tags"""
        elem = constructors.new_element("text", text="text here")
        del(elem.attrib["id"])
        assert etree.tostring(elem) == b"<text>text here</text>"

    def test_float(self) -> None:
        """Floats at 0.6f precision"""
        elem = constructors.new_element("text", x=1 / 3)
        del(elem.attrib["id"])
        assert etree.tostring(elem) == b'<text x="0.333333"/>'


class TestNewSubElement:
    def test_sub_element(self) -> None:
        """New element is a sub-element of parent"""
        parent = constructors.new_element("g")
        rect = constructors.new_sub_element(parent, "rect")
        del(parent.attrib["id"])
        del(rect.attrib["id"])
        assert etree.tostring(parent) == b"<g><rect/></g>"


class TestUpdateElement:
    def test_new_params(self) -> None:
        """New params added"""
        elem = constructors.new_element("line", x=10, y1=80)
        _ = constructors.update_element(elem, stroke_width=2)
        del(elem.attrib["id"])
        assert etree.tostring(elem) == b'<line x="10" y1="80" stroke-width="2"/>'


class TestDeepcopyElement:
    def test_is_copy(self) -> None:
        """"""
        group = constructors.new_element("g", id_=1)
        line = constructors.new_sub_element(group, "line", x=10, y1=80, id_=2)
        group_copy = constructors.deepcopy_element(group, stroke="black")
        assert line in group
        assert line not in group_copy

    def test_attributes_except_id_match(self):
        """Attributes match except"""
        group = constructors.new_element("g", stroke="black", id_=1)
        line = constructors.new_sub_element(group, "line", x=10, y1=80, id_=2)
        group_copy = constructors.deepcopy_element(group)
        assert group.attrib == group_copy.attrib
        assert line.attrib == group_copy[0].attrib

