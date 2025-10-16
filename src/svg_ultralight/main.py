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

from pathlib import Path
from typing import IO, TYPE_CHECKING, TypeGuard

from lxml import etree

from svg_ultralight.constructors import update_element
from svg_ultralight.layout import pad_and_scale
from svg_ultralight.nsmap import NSMAP
from svg_ultralight.string_conversion import get_view_box_str, svg_tostring

if TYPE_CHECKING:
    import os

    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )

    from svg_ultralight.attrib_hints import ElemAttrib, OptionalElemAttribMapping
    from svg_ultralight.layout import PadArg


def _is_io_bytes(obj: object) -> TypeGuard[IO[bytes]]:
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
    attrib: OptionalElemAttribMapping | None = None,
    **attributes: ElemAttrib,
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
    :param attrib: optionally pass additional attributes as a mapping instead of as
        anonymous kwargs. This is useful for pleasing the linter when unpacking a
        dictionary into a function call.
    :param attributes: element attribute names and values
    :return: root svg element

    * dimension strings are strings with a float value and a unit. Valid units
      are formatted as "1in", "2cm", or "3mm".

    All viewBox-style (trailing underscore) parameters are optional. Any kwargs
    will be passed to ``etree.Element`` as element parameters. These will
    supercede any parameters inferred from the trailing underscore parameters.
    """
    attributes.update(attrib or {})
    if nsmap is None:
        nsmap = NSMAP

    inferred_attribs: dict[str, ElemAttrib] = {}
    if (
        isinstance(x_, (float, int))
        and isinstance(y_, (float, int))
        and isinstance(width_, (float, int))
        and isinstance(height_, (float, int))
    ):
        padded_viewbox, scale_attribs = pad_and_scale(
            (x_, y_, width_, height_), pad_, print_width_, print_height_, dpu_
        )
        inferred_attribs["viewBox"] = get_view_box_str(*padded_viewbox)
        inferred_attribs.update(scale_attribs)
    inferred_attribs.update(attributes)
    # can only pass nsmap on instance creation
    svg_root = etree.Element(f"{{{nsmap[None]}}}svg", nsmap=nsmap)
    return update_element(svg_root, **inferred_attribs)


def write_svg(
    svg: str | Path | IO[bytes],
    root: EtreeElement,
    stylesheet: str | os.PathLike[str] | None = None,
    *,
    do_link_css: bool = False,
    **tostring_kwargs: str | bool,
) -> str:
    r"""Write an xml element as an svg file.

    :param svg: open binary file object or path to output file (include extension .svg)
    :param root: root node of your svg geometry
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
            root.addprevious(link)
        else:
            style = etree.Element("style", type="text/css")
            with Path(stylesheet).open(encoding="utf-8") as css_file:
                style.text = etree.CDATA("\n" + "".join(css_file.readlines()) + "\n")
            root.insert(0, style)

    svg_contents = svg_tostring(root, **tostring_kwargs)

    if _is_io_bytes(svg):
        _ = svg.write(svg_contents)
        return svg.name
    if isinstance(svg, (str, Path)):
        with Path(svg).open("wb") as svg_file:
            _ = svg_file.write(svg_contents)
        return str(svg)
    msg = f"svg must be a path-like object or a file-like object, not {type(svg)}"
    raise TypeError(msg)
