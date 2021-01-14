#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
"""Simple functions to LIGHTLY assist in creating Scalable Vector Graphics.

:author: Shay Hill
created: 10/7/2019

Some functions here require a path to an Inkscape executable on your filesystem.
IMPORTANT: path cannot end with ``.exe``.
Use something like ``"C:\\Program Files\\Inkscape\\inkscape"``
"""

import math
import os
from pathlib import Path
from subprocess import call
from tempfile import NamedTemporaryFile
from typing import Dict, IO, Optional, Union

from lxml import etree  # type: ignore

from .constructors import update_element
from .nsmap import NSMAP
from .string_conversion import get_viewBox_str, svg_tostring


def new_svg_root(
    x_: Optional[float] = None,
    y_: Optional[float] = None,
    width_: Optional[float] = None,
    height_: Optional[float] = None,
    pad_: float = 0,
    dpu_: float = 1,
    nsmap: Optional[Dict[str, str]] = None,
    **attributes: Union[float, str],
) -> etree.Element:
    """
    Create an svg root element from viewBox style parameters.

    :param x_: x value in upper-left corner
    :param y_: y value in upper-left corner
    :param width_: width of viewBox
    :param height_: height of viewBox
    :param pad_: optionally increase viewBox by pad in all directions
    :param dpu_: optionally scale image (pixels per unit of bounding box)
    :param attributes: element attribute names and values
    :param nsmap: optionally pass a namespace map of your choosing
    :return: root svg element

    All viewBox-style (trailing underscore) parameters are optional. Any kwargs will
    be passed to ``etree.Element`` as element parameters. Float values to
    trailing-underscore parameters will be rounded to ints. Float arguments cause
    problems with bounding boxes. If you don't query bounding boxes, you may never
    notice.
    """
    if nsmap is None:
        nsmap = NSMAP
    if None not in (x_, y_, width_, height_):
        view_box = get_viewBox_str(x_, y_, width_, height_, pad_)
        pixel_width = str(math.floor((width_ + pad_ * 2) * dpu_ + 0.5))
        pixel_height = str(math.floor((height_ + pad_ * 2) * dpu_ + 0.5))
        attributes["viewBox"] = attributes.get("viewBox", view_box)
        attributes["width"] = attributes.get("width", pixel_width)
        attributes["height"] = attributes.get("height", pixel_height)
    # can only pass nsmap on instance creation
    svg_root = etree.Element(f"{{{nsmap[None]}}}svg", nsmap=nsmap)
    return update_element(svg_root, **attributes)


def write_svg(
    svg: Union[str, IO[bytes]],
    xml: etree.Element,
    stylesheet: Optional[str] = None,
    do_link_css: bool = False,
    **tostring_kwargs,
) -> str:
    """
    Write an xml element as an svg file.

    :param svg: open binary file object or path to output file (include extension .svg)
    :param xml: root node of your svg geometry
    :param stylesheet: optional path to css stylesheet
    :param do_link_css: link to stylesheet, else (default) write contents of stylesheet
        into svg (ignored if stylesheet is None)
    :param tostring_kwargs: keyword arguments to etree.tostring. xml_header=True for
        sensible default values. See below.
    :return: svg filename
    :effects: creates svg file at ``svg``

    It's often useful to write a temporary svg file, so a tempfile.NamedTemporaryFile
    object (or any open binary file object can be passed instead of an svg filename).

    You may never need an xml_header. Inkscape doesn't need it, your browser doesn't
    need it, and it's forbidden if you'd like to "inline" your svg in an html file.
    The most pressing need might be to set an encoding. If you pass
    ``xml_declaration=True`` as a tostring_kwarg, this function will attempt to pass
    the following defaults to ``lxml.etree.tostring``:

    * doctype: str = (
        '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n'
        '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
    )
    * encoding = "UTF-8"

    Always, this function will default to ``pretty_print=True``

    These can be overridden by tostring_kwargs.

    e.g., ``write_svg(..., xml_declaration=True, doctype=None``)
    e.g., ``write_svg(..., xml_declaration=True, encoding='ascii')``

    ``lxml.etree.tostring`` is documented here: https://lxml.de/api/index.html,
    but I know that to be incomplete as of 2020 Feb 01, as it does not document the
    (perhaps important to you) 'encoding' kwarg.
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
            with open(stylesheet) as css_file:
                style.text = etree.CDATA("\n" + "".join(css_file.readlines()) + "\n")
            xml.insert(0, style)

    svg_contents = svg_tostring(xml, **tostring_kwargs)

    try:
        svg.write(svg_contents)
        return svg.name
    except AttributeError:
        with open(svg, "wb") as svg_file:
            svg_file.write(svg_contents)
        return svg


def write_png_from_svg(inkscape: str, svg: str, png: Optional[str] = None) -> str:
    """
    Convert an svg file to a png

    :param inkscape: path to inkscape executable (without .exe extension!)
    :param svg: path to svg file
    :param png: optional path to png output file
    :return: png filename
    :effects: creates a new png from svg filename

    If no output png path is given, the output path will be inferred from the ``svg``
    filename.
    """
    if png is None:
        png = str(Path(svg).with_suffix(".png"))
    call(f'"{inkscape}" -f "{svg}" -e "{png}"')
    return png


def write_png(
    inkscape: str, png: str, xml: etree.Element, stylesheet: Optional[str] = None,
) -> str:
    """
    Create a png file without writing an intermediate svg file.

    :param inkscape: path to inkscape executable (without .exe extension!)
    :param png: path to output png file
    :param xml: root node of your svg geometry
    :param stylesheet: optional path to css stylesheet
    :return: png filename (the same you input as ``png``)
    :effects: creates a new png file

    This just creates a tempfile, writes the svg to the tempfile, then calls
    ``write_png_from_svg`` with the tempfile. This isn't faster (it might be slightly
    slower), but it keeps the filesystem clean when you only want the png.
    """
    with NamedTemporaryFile(mode="wb", delete=False) as svg_file:
        svg = write_svg(svg_file, xml, stylesheet)
    write_png_from_svg(inkscape, svg, png)
    os.unlink(svg)
    return png
