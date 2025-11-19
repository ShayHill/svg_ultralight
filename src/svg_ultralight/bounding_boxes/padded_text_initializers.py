"""Functions that create PaddedText instances.

Three variants:

- `pad_text`: uses Inkscape to measure text bounds

- `pad_text_ft`: uses fontTools to measure text bounds (faster, and you get line_gap)

- `pad_text_mix`: uses Inkscape and fontTools to give true ascent, descent, and
  line_gap while correcting some of the layout differences between fontTools and
  Inkscape.

There is a default font size for pad_text if an element is passed. There is also a
default for the other pad_text_ functions, but it taken from the font file and is
usually 1024, so it won't be easy to miss. The default for standard pad_text is to
prevent surprises if Inksape defaults to font-size 12pt while your browser defaults
to 16px.

:author: Shay Hill
:created: 2025-06-09
"""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, overload

from svg_ultralight.bounding_boxes.bound_helpers import pad_bbox
from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.constructors import new_element, update_element
from svg_ultralight.font_tools.font_info import (
    FTFontInfo,
    get_padded_text_info,
    get_svg_font_attributes,
)
from svg_ultralight.query import get_bounding_boxes
from svg_ultralight.string_conversion import format_attr_dict, format_number

if TYPE_CHECKING:
    import os

    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )

    from svg_ultralight.attrib_hints import ElemAttrib, OptionalElemAttribMapping

DEFAULT_Y_BOUNDS_REFERENCE = "{[|gjpqyf"

# A default font size for pad_text if font-size is not specified in the reference
# element.
DEFAULT_FONT_SIZE_FOR_PAD_TEXT = 12.0  # Default font size for pad_text if not specified


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
        text_elem.attrib["font-size"] = format_number(DEFAULT_FONT_SIZE_FOR_PAD_TEXT)
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
    return PaddedText(
        text_elem,
        bbox,
        tpad,
        rpad,
        bpad,
        lpad,
        font_size=float(text_elem.attrib["font-size"]),
    )


@overload
def pad_chars_ft(
    font: str | os.PathLike[str],
    text: str,
    font_size: float | None = None,
    ascent: float | None = None,
    descent: float | None = None,
    *,
    y_bounds_reference: str | None = None,
    attrib: OptionalElemAttribMapping = None,
    **attributes: ElemAttrib,
) -> BoundElement: ...


@overload
def pad_chars_ft(
    font: str | os.PathLike[str],
    text: list[str],
    font_size: float | None = None,
    ascent: float | None = None,
    descent: float | None = None,
    *,
    y_bounds_reference: str | None = None,
    attrib: OptionalElemAttribMapping = None,
    **attributes: ElemAttrib,
) -> list[BoundElement]: ...


def pad_chars_ft(
    font: str | os.PathLike[str],
    text: str | list[str],
    font_size: float | None = None,
    ascent: float | None = None,
    descent: float | None = None,
    *,
    y_bounds_reference: str | None = None,
    attrib: OptionalElemAttribMapping = None,
    **attributes: ElemAttrib,
) -> BoundElement | list[BoundElement]:
    """Create a bound group of paths for each character in the text.

    Create a bound group of path elements, one for each character in the text. This
    will provide less utility in most respects than `pad_text_ft`, but will be useful
    for animations and other effects where individual characters need to be
    addressed.
    """
    attributes.update(attrib or {})
    attributes_ = format_attr_dict(**attributes)
    attributes_.update(get_svg_font_attributes(font))

    _ = attributes_.pop("font-size", None)
    _ = attributes_.pop("font-family", None)
    _ = attributes_.pop("font-style", None)
    _ = attributes_.pop("font-weight", None)
    _ = attributes_.pop("font-stretch", None)

    input_one_text_item = False
    if isinstance(text, str):
        input_one_text_item = True
        text = [text]
    elems: list[BoundElement] = []

    font_info = FTFontInfo(font)
    try:
        for text_item in text:
            text_info = get_padded_text_info(
                font_info,
                text_item,
                font_size,
                ascent,
                descent,
                y_bounds_reference=y_bounds_reference,
            )
            elem = text_info.new_chars_group_element(**attributes_)
            bbox = pad_bbox(text_info.bbox, text_info.padding)
            elems.append(BoundElement(elem, bbox))
    finally:
        font_info.font.close()
    if input_one_text_item:
        return elems[0]
    return elems


@overload
def pad_text_ft(
    font: str | os.PathLike[str],
    text: str,
    font_size: float | None = None,
    ascent: float | None = None,
    descent: float | None = None,
    *,
    y_bounds_reference: str | None = None,
    attrib: OptionalElemAttribMapping = None,
    **attributes: ElemAttrib,
) -> PaddedText: ...


@overload
def pad_text_ft(
    font: str | os.PathLike[str],
    text: list[str],
    font_size: float | None = None,
    ascent: float | None = None,
    descent: float | None = None,
    *,
    y_bounds_reference: str | None = None,
    attrib: OptionalElemAttribMapping = None,
    **attributes: ElemAttrib,
) -> list[PaddedText]: ...


def pad_text_ft(
    font: str | os.PathLike[str],
    text: str | list[str],
    font_size: float | None = None,
    ascent: float | None = None,
    descent: float | None = None,
    *,
    y_bounds_reference: str | None = None,
    attrib: OptionalElemAttribMapping = None,
    **attributes: ElemAttrib,
) -> PaddedText | list[PaddedText]:
    """Create a new PaddedText instance using fontTools.

    :param font: path to a font file.
    :param text: the text of the text element or a list of text strings.
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
    :param attrib: optionally pass additional attributes as a mapping instead of as
        anonymous kwargs. This is useful for pleasing the linter when unpacking a
        dictionary into a function call.
    :param attributes: additional attributes to set on the text element. There is a
        chance these will cause the font element to exceed the BoundingBox of the
        PaddedText instance.
    :return: a PaddedText instance with a line_gap defined. If a list of strings is
        given for parameter `text`, a list of PaddedText instances is returned.
    """
    attributes.update(attrib or {})
    attributes_ = format_attr_dict(**attributes)
    attributes_.update(get_svg_font_attributes(font))

    _ = attributes_.pop("font-size", None)
    _ = attributes_.pop("font-family", None)
    _ = attributes_.pop("font-style", None)
    _ = attributes_.pop("font-weight", None)
    _ = attributes_.pop("font-stretch", None)

    font_info = FTFontInfo(font)

    try:
        input_one_text_item = False
        if isinstance(text, str):
            input_one_text_item = True
            text = [text]

        elems: list[PaddedText] = []
        for text_item in text:
            text_info = get_padded_text_info(
                font_info,
                text_item,
                font_size,
                ascent,
                descent,
                y_bounds_reference=y_bounds_reference,
            )
            elem = text_info.new_element(**attributes_)
            elems.append(
                PaddedText(
                    elem,
                    text_info.bbox,
                    *text_info.padding,
                    text_info.line_gap,
                    text_info.font_size,
                )
            )
    finally:
        font_info.font.close()
    if input_one_text_item:
        return elems[0]
    return elems


def pad_text_mix(
    inkscape: str | os.PathLike[str],
    font: str | os.PathLike[str],
    text: str,
    font_size: float | None = None,
    ascent: float | None = None,
    descent: float | None = None,
    *,
    y_bounds_reference: str | None = None,
    attrib: OptionalElemAttribMapping = None,
    **attributes: ElemAttrib,
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
    :param attrib: optionally pass additional attributes as a mapping instead of as
        anonymous kwargs. This is useful for pleasing the linter when unpacking a
        dictionary into a function call.
    :param attributes: additional attributes to set on the text element. There is a
        chance these will cause the font element to exceed the BoundingBox of the
        PaddedText instance.
    :return: a PaddedText instance with a line_gap defined.
    """
    attributes.update(attrib or {})
    elem = new_element("text", text=text, **attributes)
    padded_inkscape = pad_text(inkscape, elem, y_bounds_reference, font=font)
    padded_fonttools = pad_text_ft(
        font,
        text,
        font_size,
        ascent,
        descent,
        y_bounds_reference=y_bounds_reference,
        attrib=attributes,
    )
    bbox = padded_inkscape.tbox
    rpad = padded_inkscape.rpad
    lpad = padded_inkscape.lpad
    if y_bounds_reference is None:
        tpad = padded_fonttools.tpad
        bpad = padded_fonttools.bpad
    else:
        tpad = padded_inkscape.tpad
        bpad = padded_inkscape.bpad
    return PaddedText(
        elem, bbox, tpad, rpad, bpad, lpad, padded_fonttools.line_gap, font_size
    )
