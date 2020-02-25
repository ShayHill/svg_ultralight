#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
"""Simple functions to LIGHTLY assist in creating Scalable Vector Graphics.

:author: Shay Hill
created: 10/7/2019
"""

import os
import tempfile
from enum import Enum
from pathlib import Path
from subprocess import call
from typing import Dict, Optional, Union

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


def new_svg_root(
    x_: Optional[float] = None,
    y_: Optional[float] = None,
    width_: Optional[float] = None,
    height_: Optional[float] = None,
    pad_: float = 0,
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
    :param attributes: element attribute names and values
    :param nsmap: optionally pass a namespace map of your choosing
    :return: root svg element

    All viewBox-style parameters are optional. Any kwargs will be passed to
    etree.Element as element parameters.
    """
    if nsmap is None:
        nsmap = NSMAP
    if None not in (x_, y_, width_, height_):
        view_box = f"{x_ - pad_} {y_ - pad_} {width_ + pad_ * 2} {height_ + pad_ * 2}"
        attributes["viewBox"] = attributes.get("viewBox", view_box)
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
    svg: str,
    xml: etree.Element,
    stylesheet: Optional[str] = None,
    do_link_css: bool = False,
    **tostring_kwargs,
) -> str:
    """
    Write an xml element as an svg file.

    :param svg: path to output file (include extension .svg)
    :param xml: root node of your svg geometry
    :param stylesheet: optional path to css stylesheet
    :param do_link_css: link to stylesheet, else (default) write contents of stylesheet
        into svg (ignored if stylesheet is None)
    :param tostring_kwargs: keyword arguments to etree.tostring. xml_header=True for
        sensible default values. See below.
    :return: svg filename
    :effects: creates svg file at ``svg``

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
    write_svg(svg_file.name, xml, stylesheet)
    write_png_from_svg(inkscape_exe, svg_file.name, png)
    os.unlink(svg_file.name)
    return png
