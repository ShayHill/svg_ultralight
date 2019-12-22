#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
"""Test functions in ``svg_ultralight``

:author: Shay Hill
:created: 10/25/2019

Explicitly tests string output, so any change in format will cause the tests to fail.
No tests for png writing.
"""

import os
import tempfile
from pathlib import Path

import pytest
from lxml import etree

from svg_ultralight.svg_ultralight import NSMAP, new_svg_root, write_svg


@pytest.fixture(scope="function")
def css_source():
    """Temporary css file object with meaningless contents."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as css_source:
        css_source.write("/** css for my project **/")
    yield css_source.name
    os.unlink(css_source.name)


@pytest.fixture(scope="function")
def temp_filename(mode="w"):
    """Temporary file object to capture test output output."""
    svg_output = tempfile.NamedTemporaryFile(mode=mode, delete=False)
    svg_output.close()
    yield svg_output.name
    os.unlink(svg_output.name)


class TestWriteSvg:
    def test_linked(self, css_source, temp_filename) -> None:
        """Insert stylesheet reference"""
        blank = etree.Element("blank")
        write_svg(temp_filename, blank, css_source, do_link_css=True)
        with open(temp_filename, "rb") as svg_binary:
            svg_lines = [x.decode() for x in svg_binary.readlines()]

        relative_css_path = Path(css_source).relative_to(Path(temp_filename).parent)
        assert svg_lines == [
            "<?xml version='1.0' encoding='ASCII'?>\n",
            '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n',
            '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n',
            f'<?xml-stylesheet href="{relative_css_path}" type="text/css"?>\n',
            "<blank/>\n",
        ]

    def test_not_linked(self, css_source, temp_filename) -> None:
        """Copy css_source contents into svg file"""
        blank = etree.Element("blank")
        write_svg(temp_filename, blank, css_source, do_link_css=False)
        with open(temp_filename, "rb") as svg_binary:
            svg_lines = [x.decode() for x in svg_binary.readlines()]

        assert svg_lines == [
            "<?xml version='1.0' encoding='ASCII'?>\n",
            '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n',
            '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n',
            "<blank>\n",
            '  <style type="text/css"><![CDATA[\n',
            "/** css for my project **/\n",
            "]]></style>\n",
            "</blank>\n",
        ]

    def test_css_none(self, temp_filename) -> None:
        """If css_source is None, do not link or copy in css."""
        blank = etree.Element("blank")
        write_svg(temp_filename, blank, stylesheet=None, do_link_css=True)
        with open(temp_filename, "rb") as svg_binary:
            svg_lines = [x.decode() for x in svg_binary.readlines()]

        assert svg_lines == [
            "<?xml version='1.0' encoding='ASCII'?>\n",
            '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n',
            '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n',
            "<blank/>\n",
        ]

        # test with do_link_css = False
        write_svg(temp_filename, blank, stylesheet=None, do_link_css=False)
        with open(temp_filename, "rb") as svg_binary:
            svg_lines_false = [x.decode() for x in svg_binary.readlines()]
        assert svg_lines_false == svg_lines


class TestNewSvgRoot:
    def test_args_pass(self) -> None:
        """Arguments and xmlns appear in element.

        Build the svg element namespace from NSMAP and compare to output"""
        namespace = tuple(NSMAP.items())
        xmlns = [f'xmlns="{namespace[0][1]}"']
        xmlns += [f'xmlns:{k}="{v}"' for k, v in namespace[1:]]
        svg = f'<svg {" ".join(xmlns)} viewBox="0 1 2 3"/>'.encode()
        assert etree.tostring(new_svg_root(0, 1, 2, 3)) == svg
