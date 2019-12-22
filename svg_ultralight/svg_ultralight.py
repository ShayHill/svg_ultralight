#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
"""Simple functions to LIGHTLY assist in creating Scalable Vector Graphics.

:author: Shay Hill
created: 10/7/2019
"""

import os
import tempfile
from pathlib import Path
from subprocess import call
from typing import Optional

from lxml import etree  # type: ignore

_SVG_NAMESPACE = "http://www.w3.org/2000/svg"
NSMAP = {
    None: _SVG_NAMESPACE,
    "dc": "http://purl.org/dc/elements/1.1/",
    "cc": "http://creativecommons.org/ns#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "svg": _SVG_NAMESPACE,
    "xlink": "http://www.w3.org/1999/xlink",
    "sodipodi": "http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd",
    "inkscape": "http://www.inkscape.org/namespaces/inkscape",
}


def new_svg_root(
    x: float, y: float, width: float, height: float, pad: float = 0
) -> etree.Element:
    """
    Create an svg root element from viewBox style params.

    :param x: x value in upper-left corner
    :param y: y value in upper-left corner
    :param width: width of viewBox
    :param height: height of viewBox
    :param pad: optionally increase viewBox by pad in all directions
    :return: root svg element
    """
    return etree.Element(
        "svg",
        viewBox=f"{x - pad} {y - pad} {width + pad * 2} {height + pad * 2}",
        nsmap=NSMAP,
    )


def write_svg(
    svg: str,
    xml: etree.Element,
    stylesheet: Optional[str] = None,
    do_link_css: bool = False,
) -> str:
    """
    Write an xml element as an svg file.

    :param svg: path to output file (include extension .svg)
    :param xml: root node of your svg geometry
    :param stylesheet: optional path to css stylesheet
    :param do_link_css: link to stylesheet, else (default) write contents of stylesheet
        into svg (ignored if stylesheet is None)
    :return: svg filename
    :effects: creates svg file at ``svg``
    """
    if stylesheet is not None:
        if do_link_css is True:
            relative_css_path = Path(stylesheet).relative_to(Path(svg).parent)
            link = etree.PI(
                "xml-stylesheet", f'href="{relative_css_path}" type="text/css"'
            )
            xml.addprevious(link)
        else:
            style = etree.Element("style", type="text/css")
            with open(stylesheet, "r") as css_file:
                style.text = etree.CDATA("\n" + "".join(css_file.readlines()) + "\n")
            xml.insert(0, style)

    svg_contents = etree.tostring(
        etree.ElementTree(xml),
        pretty_print=True,
        xml_declaration=True,
        doctype=(
            '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n'
            '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
        ),
    )
    with open(svg, "wb") as svg_file:
        svg_file.write(svg_contents)
    return svg


def write_png_from_svg(inkscape_exe: str, svg: str, png: Optional[str] = None) -> str:
    """
    Convert an svg file to a png

    :param inkscape_exe: path to inkscape.exe
    :param svg: path to svg file
    :param png: optional path to png output file
    :return: png filename
    :effects: creates a new png from svg filename

    If no output png path is given, the output path will be inferred from the ``svg``
    filename.
    """
    if png is None:
        png = str(Path(svg).with_suffix(".png"))
    call(f'"{inkscape_exe}" -f "{svg}" -e "{png}"')
    return png


def write_png(
    inkscape_exe: str, png: str, xml: etree.Element, stylesheet: Optional[str] = None,
) -> str:
    """
    Create a png file without writing an intermediate svg file.

    :param inkscape_exe: path to inkscape.exe
    :param png: path to output png file
    :param xml: root node of your svg geometry
    :param stylesheet: optional path to css stylesheet
    :return: png filename (the same you input as ``png``)
    :effects: creates a new png file

    This just creates a tempfile, writes the svg to the tempfile, then calls
    ``write_png_from_svg`` with the tempfile. This isn't faster (it might be slightly
    slower), but it keeps the filesystem clean when you only want the png.
    """
    svg_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    svg_file.close()
    write_svg(svg_file.name, xml, stylesheet, do_link_css=False)
    write_png_from_svg(inkscape_exe, svg_file.name, png)
    os.unlink(svg_file.name)
    return png
