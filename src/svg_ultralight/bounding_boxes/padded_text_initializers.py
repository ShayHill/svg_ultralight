"""Functions that create PaddedText instances.

:author: Shay Hill
:created: 2025-06-09
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING

from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.constructors import new_element, update_element
from svg_ultralight.font_tools.font_info import (
    get_padded_text_info,
    get_svg_font_attributes,
)
from svg_ultralight.font_tools.globs import DEFAULT_FONT_SIZE
from svg_ultralight.query import get_bounding_boxes
from svg_ultralight.string_conversion import (
    encode_to_css_class_name,
    format_attr_dict,
    format_number,
)

if TYPE_CHECKING:
    import os

    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )

DEFAULT_Y_BOUNDS_REFERENCE = "{[|gjpqyf"


def pad_text(
    inkscape: str | os.PathLike[str],
    text_elem: EtreeElement,
    y_bounds_reference: str | None = None,
    *,
    font: str | os.PathLike[str] | None = None,
) -> PaddedText:
    r"""Create a PaddedText instance from a text element.

    :param inkscape: path to an inkscape executable on your local file system
        IMPORTANT: path cannot end with ``.exe``.
        Use something like ``"C:\\Program Files\\Inkscape\\inkscape"``
    :param text_elem: an etree element with a text tag
    :param y_bounds_reference: an optional string to use to determine the ascent and
        capline of the font. The default is a good choice, which approaches or even
        meets the ascent of descent of most fonts without using utf-8 characters. You
        might want to use a letter like "M" or even "x" if you are using an all-caps
        string and want to center between the capline and baseline or if you'd like
        to center between the baseline and x-line.
    :param font: optionally add a path to a font file to use for the text element.
        This is going to conflict with any font-family, font-style, or other
        font-related attributes *except* font-size. You likely want to use
        `font_tools.new_padded_text` if you're going to pass a font path, but you can
        use it here to compare results between `pad_text` and `new_padded_text`.
    :return: a PaddedText instance
    """
    if y_bounds_reference is None:
        y_bounds_reference = DEFAULT_Y_BOUNDS_REFERENCE
    if font is not None:
        _ = update_element(text_elem, **get_svg_font_attributes(font))
    if "font-size" not in text_elem.attrib:
        text_elem.attrib["font-size"] = format_number(DEFAULT_FONT_SIZE)
    rmargin_ref = deepcopy(text_elem)
    capline_ref = deepcopy(text_elem)
    _ = rmargin_ref.attrib.pop("id", None)
    _ = capline_ref.attrib.pop("id", None)
    rmargin_ref.attrib["text-anchor"] = "end"
    capline_ref.text = y_bounds_reference

    bboxes = get_bounding_boxes(inkscape, text_elem, rmargin_ref, capline_ref)
    bbox, rmargin_bbox, capline_bbox = bboxes

    tpad = bbox.y - capline_bbox.y
    rpad = -rmargin_bbox.x2
    bpad = capline_bbox.y2 - bbox.y2
    lpad = bbox.x
    return PaddedText(text_elem, bbox, tpad, rpad, bpad, lpad)


def pad_text_ft(
    font: str | os.PathLike[str],
    text: str,
    font_size: float = DEFAULT_FONT_SIZE,
    ascent: float | None = None,
    descent: float | None = None,
    *,
    y_bounds_reference: str | None = None,
    **attributes: str | float,
) -> PaddedText:
    """Create a new PaddedText instance using fontTools.

    :param font: path to a font file.
    :param text: the text of the text element.
    :param font_size: the font size to use.
    :param ascent: the ascent of the font. If not provided, it will be calculated
        from the font file.
    :param descent: the descent of the font. If not provided, it will be calculated
        from the font file.
    :param y_bounds_reference: optional character or string to use as a reference
        for the ascent and descent. If provided, the ascent and descent will be the y
        extents of the capline reference. This argument is provided to mimic the
        behavior of the query module's `pad_text` function. `pad_text` does no
        inspect font files and relies on Inkscape to measure reference characters.
    :param attributes: additional attributes to set on the text element. There is a
        chance these will cause the font element to exceed the BoundingBox of the
        PaddedText instance.
    :return: a PaddedText instance with a line_gap defined.
    """
    attributes_ = format_attr_dict(**attributes)
    attributes_["font-size"] = attributes_.get("font-size", format_number(font_size))
    attributes_["class"] = encode_to_css_class_name(Path(font).name)

    elem = new_element("text", text=text, **attributes_)
    info = get_padded_text_info(
        font, text, font_size, ascent, descent, y_bounds_reference=y_bounds_reference
    )
    return PaddedText(elem, info.bbox, *info.padding, info.line_gap)


def pad_text_mix(
    inkscape: str | os.PathLike[str],
    font: str | os.PathLike[str],
    text: str,
    font_size: float = DEFAULT_FONT_SIZE,
    ascent: float | None = None,
    descent: float | None = None,
    *,
    y_bounds_reference: str | None = None,
    **attributes: str | float,
) -> PaddedText:
    """Use Inkscape text bounds and fill missing with fontTools.

    :param font: path to a font file.
    :param text: the text of the text element.
    :param font_size: the font size to use.
    :param ascent: the ascent of the font. If not provided, it will be calculated
        from the font file.
    :param descent: the descent of the font. If not provided, it will be calculated
        from the font file.
    :param y_bounds_reference: optional character or string to use as a reference
        for the ascent and descent. If provided, the ascent and descent will be the y
        extents of the capline reference. This argument is provided to mimic the
        behavior of the query module's `pad_text` function. `pad_text` does no
        inspect font files and relies on Inkscape to measure reference characters.
    :param attributes: additional attributes to set on the text element. There is a
        chance these will cause the font element to exceed the BoundingBox of the
        PaddedText instance.
    :return: a PaddedText instance with a line_gap defined.
    """
    elem = new_element("text", text=text, **attributes)
    padded_inkscape = pad_text(inkscape, elem, y_bounds_reference, font=font)
    padded_fonttools = pad_text_ft(
        font,
        text,
        font_size,
        ascent,
        descent,
        y_bounds_reference=y_bounds_reference,
        **attributes,
    )
    bbox = padded_inkscape.unpadded_bbox
    rpad = padded_inkscape.rpad
    lpad = padded_inkscape.lpad
    if y_bounds_reference is None:
        tpad = padded_fonttools.tpad
        bpad = padded_fonttools.bpad
    else:
        tpad = padded_inkscape.tpad
        bpad = padded_inkscape.bpad
    return PaddedText(elem, bbox, tpad, rpad, bpad, lpad, padded_fonttools.line_gap)
