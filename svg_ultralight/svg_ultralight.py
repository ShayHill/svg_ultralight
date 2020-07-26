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
import tempfile
from enum import Enum
from pathlib import Path
from subprocess import call
from typing import Dict, IO, Optional, Union

from lxml import etree  # type: ignore

from .constructors import update_element

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


def _get_viewBox_str(
    x: float, y: float, width: float, height: float, pad: float = 0
) -> str:
    """
    Round arguments to ints and create a space-delimited string.

    :param x: x value in upper-left corner
    :param y: y value in upper-left corner
    :param width: width of viewBox
    :param height: height of viewBox
    :param pad: optionally increase viewBox by pad in all directions
    :return: space-delimited string "x y width height"
    """
    dims = [
        str(round(a + b))
        for a, b in zip((x, y, width, height), (-pad, -pad, pad * 2, pad * 2))
    ]
    return " ".join(dims)


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
        view_box = _get_viewBox_str(x_, y_, width_, height_, pad_)
        pixel_width = str(math.floor((width_ + pad_ * 2) * dpu_ + 0.5))
        pixel_height = str(math.floor((height_ + pad_ * 2) * dpu_ + 0.5))
        attributes["viewBox"] = attributes.get("viewBox", view_box)
        attributes["width"] = attributes.get("width", pixel_width)
        attributes["height"] = attributes.get("height", pixel_height)
    # can only pass nsmap on instance creation
    svg_root = etree.Element("svg", nsmap=nsmap)
    return update_element(svg_root, **attributes)


class _TostringDefaults(Enum):
    """Default values for an svg xml_header"""

    doctype: str = (
        '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN"\n'
        '"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
    )
    encoding: str = "UTF-8"


def _svg_tostring(xml: etree.Element, **tostring_kwargs) -> bytearray:
    """
    Contents of svg file with optional xml declaration.

    :param xml: root node of your svg geometry
    :param tostring_kwargs: keyword arguments to etree.tostring. xml_header=True for
        sensible default values. See below.

    Further documentation in write_svg docstring.
    """
    tostring_kwargs["pretty_print"] = tostring_kwargs.get("pretty_print", True)
    if tostring_kwargs.get("xml_declaration"):
        for default in _TostringDefaults:
            value = tostring_kwargs.get(default.name, default.value)
            tostring_kwargs[default.name] = value
    svg_contents = etree.tostring(etree.ElementTree(xml), **tostring_kwargs)
    return svg_contents


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

    svg_contents = _svg_tostring(xml, **tostring_kwargs)

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
    svg_file = tempfile.NamedTemporaryFile(mode="w", delete=False)
    svg_file.close()
    write_svg(svg_file.name, xml, stylesheet)
    write_png_from_svg(inkscape, svg_file.name, png)
    os.unlink(svg_file.name)
    return png
