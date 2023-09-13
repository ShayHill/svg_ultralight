r"""Simple functions to LIGHTLY assist in creating Scalable Vector Graphics.

:author: Shay Hill
created: 10/7/2019

Some functions here require a path to an Inkscape executable on your filesystem.
IMPORTANT: path cannot end with ``.exe``.
Use something like ``"C:\\Program Files\\Inkscape\\inkscape"``

Inkscape changed their command-line interface with version 1.0. These functions
should work with all Inkscape versions. Please report any issues.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import IO, TYPE_CHECKING

from lxml import etree

from svg_ultralight.constructors import update_element
from svg_ultralight.layout import pad_and_scale
from svg_ultralight.nsmap import NSMAP
from svg_ultralight.string_conversion import get_viewBox_str, svg_tostring

if TYPE_CHECKING:
    from lxml.etree import _Element as EtreeElement  # type: ignore

    from svg_ultralight.layout import PadArg


def _is_four_floats(objs: tuple[object, ...]) -> bool:
    """Is obj a 4-tuple of numbers?.

    :param objs: list of objects
    :return: True if all objects are numbers and there are 4 of them
    """
    return len(objs) == 4 and all(isinstance(x, (float, int)) for x in objs)


def _is_io_bytes(obj: object) -> bool:
    """Determine if an object is file-like.

    :param obj: object
    :return: True if object is file-like
    """
    return hasattr(obj, "read") and hasattr(obj, "write")


def new_svg_root(
    x_: float | None = None,
    y_: float | None = None,
    width_: float | None = None,
    height_: float | None = None,
    *,
    pad_: PadArg = 0,
    print_width_: float | str | None = None,
    print_height_: float | str | None = None,
    dpu_: float = 1,
    nsmap: dict[str | None, str] | None = None,
    **attributes: float | str,
) -> EtreeElement:
    """Create an svg root element from viewBox style parameters.

    :param x_: x value in upper-left corner
    :param y_: y value in upper-left corner
    :param width_: width of viewBox
    :param height_: height of viewBox
    :param pad_: optionally increase viewBox by pad in all directions. Acceps a
        single value or a tuple of values applied to (cycled over) top, right,
        bottom, left. pad can be floats or dimension strings*
    :param print_width_: optionally explicitly set unpadded width in units
        (float) or a dimension string*
    :param print_height_: optionally explicitly set unpadded height in units
        (float) or a dimension string*
    :param dpu_: dots per unit. Scale the output by this factor. This is
        different from print_width_ and print_height_ in that dpu_ scales the
        *padded* output.
    :param nsmap: optionally pass a namespace map of your choosing
    :param attributes: element attribute names and values
    :return: root svg element

    * dimension strings are strings with a float value and a unit. Valid units
      are formatted as "1in", "2cm", or "3mm".

    All viewBox-style (trailing underscore) parameters are optional. Any kwargs
    will be passed to ``etree.Element`` as element parameters. These will
    supercede any parameters inferred from the trailing underscore parameters.
    """
    if nsmap is None:
        nsmap = NSMAP

    inferred_attribs: dict[str, float | str] = {}
    view_box_args = (x_, y_, width_, height_)
    if _is_four_floats(view_box_args):
        assert isinstance(x_, (float, int))
        assert isinstance(y_, (float, int))
        assert isinstance(width_, (float, int))
        assert isinstance(height_, (float, int))
        padded_viewbox, scale_attribs = pad_and_scale(
            (x_, y_, width_, height_), pad_, print_width_, print_height_, dpu_
        )
        inferred_attribs["viewBox"] = get_viewBox_str(*padded_viewbox)
        inferred_attribs.update(scale_attribs)
    inferred_attribs.update(attributes)
    # can only pass nsmap on instance creation
    svg_root = etree.Element(f"{{{nsmap[None]}}}svg", nsmap=nsmap)
    return update_element(svg_root, **inferred_attribs)


def write_svg(
    svg: Path | str | IO[bytes],
    xml: EtreeElement,
    stylesheet: Path | str | None = None,
    *,
    do_link_css: bool = False,
    **tostring_kwargs: str | bool,
) -> str:
    r"""Write an xml element as an svg file.

    :param svg: open binary file object or path to output file (include extension .svg)
    :param xml: root node of your svg geometry
    :param stylesheet: optional path to css stylesheet
    :param do_link_css: link to stylesheet, else (default) write contents of stylesheet
        into svg (ignored if stylesheet is None)
    :param tostring_kwargs: keyword arguments to etree.tostring. xml_header=True for
        sensible default values. See below.
    :return: svg filename
    :effects: creates svg file at ``svg``
    :raises TypeError: if ``svg`` is not a Path, str, or binary file object

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
            parent = Path(str(svg)).parent
            relative_css_path = Path(stylesheet).relative_to(parent)
            link = etree.PI(
                "xml-stylesheet", f'href="{relative_css_path}" type="text/css"'
            )
            xml.addprevious(link)
        else:
            style = etree.Element("style", type="text/css")
            with Path(stylesheet).open(encoding="utf-8") as css_file:
                style.text = etree.CDATA("\n" + "".join(css_file.readlines()) + "\n")
            xml.insert(0, style)

    svg_contents = svg_tostring(xml, **tostring_kwargs)

    if _is_io_bytes(svg):
        _ = svg.write(svg_contents)  # type: ignore
        return svg.name  # type: ignore
    if isinstance(svg, (Path, str)):
        with Path(svg).open("wb") as svg_file:
            _ = svg_file.write(svg_contents)
        return str(svg)
    msg = f"svg must be a path-like object or a file-like object, not {type(svg)}"
    raise TypeError(msg)


def write_png_from_svg(
    inkscape: Path | str, svg: Path | str, png: Path | str | None = None
) -> str:
    """Convert an svg file to a png.

    :param inkscape: path to inkscape executable (without .exe extension!)
    :param svg: path to svg file
    :param png: optional path to png output file
    :return: png filename
    :effects: creates a new png from svg filename
    :raises ValueError: if unable to write png. This could result from an error with
        Inkscape.

    If no output png path is given, the output path will be inferred from the ``svg``
    filename.
    """
    png = str(Path(svg).with_suffix(".png")) if png is None else str(png)

    # inkscape versions >= 1.0
    options = [f'"{svg}"', "--export-type=png", f'--export-filename="{png}"']
    return_code = subprocess.call(f'"{inkscape}" ' + " ".join(options))
    if return_code == 0:
        return png

    # inkscape versions < 1.0
    return_code = subprocess.call(f'"{inkscape}" -f "{svg}" -e "{png}"')
    if return_code == 0:
        return png

    msg = f"failed to write {png} with inkscape {inkscape}"
    raise ValueError(msg)


def write_png(
    inkscape: Path | str,
    png: Path | str,
    xml: EtreeElement,
    stylesheet: str | None = None,
) -> str:
    """Create a png file without writing an intermediate svg file.

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
    _ = write_png_from_svg(inkscape, svg, png)
    os.unlink(svg)
    return str(png)


def write_pdf_from_svg(
    inkscape: Path | str, svg: Path | str, pdf: Path | str | None = None
) -> str:
    """Convert an svg file to a pdf.

    :param inkscape: path to inkscape executable (without .exe extension!)
    :param svg: path to svg file
    :param pdf: optional path to png output file
    :return: pdf filename
    :effects: creates a new pfd from svg filename
    :raises ValueError: if unable to write pdf. This could result from an error with
        Inkscape.

    If no output png path is given, the output path will be inferred from the ``svg``
    filename.
    """
    pdf = str(Path(svg).with_suffix(".pdf")) if pdf is None else str(pdf)

    # inkscape versions >= 1.0
    options = [f'"{svg}"', "--export-type=pdf", f'--export-filename="{pdf}"']
    return_code = subprocess.call(f'"{inkscape}" ' + " ".join(options))
    if return_code == 0:
        return pdf

    # inkscape versions < 1.0
    return_code = subprocess.call(f'"{inkscape}" -f "{svg}" -e "{pdf}"')
    if return_code == 0:
        return pdf

    msg = f"failed to write {pdf} from {svg}"
    raise ValueError(msg)


def write_pdf(
    inkscape: Path | str,
    pdf: Path | str,
    xml: EtreeElement,
    stylesheet: Path | str | None = None,
) -> str:
    """Create a pdf file without writing an intermediate svg file.

    :param inkscape: path to inkscape executable (without .exe extension!)
    :param pdf: path to output pdf file
    :param xml: root node of your svg geometry
    :param stylesheet: optional path to css stylesheet
    :return: pdf filename (the same you input as ``pdf``)
    :effects: creates a new pdf file

    This just creates a tempfile, writes the svg to the tempfile, then calls
    ``write_pdf_from_svg`` with the tempfile. This isn't faster (it might be slightly
    slower), but it keeps the filesystem clean when you only want the pdf.
    """
    with NamedTemporaryFile(mode="wb", delete=False) as svg_file:
        svg = write_svg(svg_file, xml, stylesheet)
    _ = write_pdf_from_svg(inkscape, svg, pdf)
    os.unlink(svg)
    return str(pdf)
