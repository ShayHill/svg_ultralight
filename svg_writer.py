#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
"""Simple functions to LIGHTLY assist in creating Scalable Vector Graphics.

:author: Shay Hill
created: 10/7/2019
"""

from pathlib import Path
from subprocess import call
from typing import Optional, Union

from lxml import etree

PathType = Union[Path, str]


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
        xmlns="http://www.w3.org/2000/svg",
    )


def write_svg(
    filename: PathType,
    xml: etree.Element,
    stylesheet: Optional[PathType] = None,
    do_link_css: bool = True,
) -> None:
    """
    Write an xml element as an svg file.

    :param filename: path to output file (include extension .svg)
    :param xml: root node of your svg geometry
    :param stylesheet: optional path to css stylesheet
    :param do_link_css: link to stylesheet, else write contents of stylesheet into svg
        (ignored if stylesheet is None)
    :return: None
    :side effect: creates svg file at ``filename``
    """
    if stylesheet is not None:
        if do_link_css is True:
            relative_css_path = Path(stylesheet).relative_to(Path(filename).parent)
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
    with open(filename, "wb") as svg_file:
        svg_file.write(svg_contents)


def write_png_from_svg(inkscape_exe: PathType, svg: PathType) -> Path:
    """
    Convert an svg file to a png

    :param inkscape_exe: path to inkscape.exe
    :param svg: path to svg file
    :return: png filename
    :side effect: creates a new png from svg filename
    """
    png = Path(svg).with_suffix(".png")
    call(f'"{inkscape_exe}" -f "{svg}" -e "{png}"')
    return png
