"""Functions that create PaddedText instances.

Three variants:

- `pad_text`: uses Inkscape to measure text bounds

- `pad_text_ft`: uses fontTools to measure text bounds (faster, and you get line_gap)

There is a default font size for pad_text if an element is passed. There is also a
default for the other pad_text_ functions, but it taken from the font file and is
usually 1024, so it won't be easy to miss. The default for standard pad_text is to
prevent surprises if Inksape defaults to font-size 12pt while your browser defaults
to 16px.

:author: Shay Hill
:created: 2025-06-09
"""

from __future__ import annotations

import itertools as it
from copy import deepcopy
from typing import TYPE_CHECKING, overload

from svg_ultralight.attrib_hints import ElemAttrib
from svg_ultralight.bounding_boxes.type_padded_text import (
    FontMetrics,
    PaddedText,
    new_padded_union,
)
from svg_ultralight.constructors import update_element
from svg_ultralight.font_tools.font_info import (
    DATA_TEXT_ESCAPE_CHARS,
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


def _desanitize_svg_data_text(text: str) -> str:
    """Desanitize a string from an SVG data-text attribute.

    :param text: The input string to desanitize.
    :return: The desanitized string with XML characters unescaped.
    """
    for char, escape_seq in DATA_TEXT_ESCAPE_CHARS.items():
        text = text.replace(escape_seq, char)
    return text


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


def _remove_svg_font_attributes(attributes: dict[str, ElemAttrib]) -> dict[str, str]:
    """Remove svg font attributes from the attributes dict.

    These are either not required when explicitly passing a font file, not relevant,
    or not supported by fontTools.
    """
    attributes_ = format_attr_dict(**attributes)
    keys_to_remove = [
        "font-size",
        "font-family",
        "font-style",
        "font-weight",
        "font-stretch",
    ]
    return {k: v for k, v in attributes_.items() if k not in keys_to_remove}


def join_tspans(
    font: str | os.PathLike[str],
    tspans: list[PaddedText],
    attrib: OptionalElemAttribMapping = None,
) -> PaddedText:
    """Join multiple PaddedText elements into a single BoundElement.

    :param font: the one font file used for kerning.
    :param tspans: list of tspan elements to join (each an output from pad_chars_ft).

    This is limited and will not handle arbitrary text elements (only `g` elements
    with a "data-text" attribute equal to the character(s) in the tspan). Will also
    not handle scaled PaddedText instances. This is for joining tspans originally
    after they are created and all using similar fonts.
    """
    font_info = FTFontInfo(font)
    for left, right in it.pairwise(tspans):
        l_joint = _desanitize_svg_data_text(left.elem.attrib["data-text"])[-1]
        r_joint = _desanitize_svg_data_text(right.elem.attrib["data-text"])[0]
        l_name = font_info.get_glyph_name(l_joint)
        r_name = font_info.get_glyph_name(r_joint)
        kern = font_info.kern_table.get((l_name, r_name), 0)
        right.x = left.x2 + kern
    return new_padded_union(*tspans, **attrib or {})


@overload
def pad_text_ft(
    font: str | os.PathLike[str] | FTFontInfo,
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
    font: str | os.PathLike[str] | FTFontInfo,
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
    font: str | os.PathLike[str] | FTFontInfo,
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
    attributes_ = _remove_svg_font_attributes(attributes)

    input_one_text_item = False
    if isinstance(text, str):
        input_one_text_item = True
        text = [text]

    font_info = FTFontInfo(font)
    metrics = FontMetrics(
        units_per_em=font_info.units_per_em,
        ascent=font_info.ascent,
        descent=font_info.descent,
        line_gap=font_info.line_gap,
        cap_height=font_info.cap_height,
        x_height=font_info.x_height,
    )

    elems: list[PaddedText] = []
    for text_item in text:
        ti = get_padded_text_info(
            font_info,
            text_item,
            font_size,
            ascent,
            descent,
            y_bounds_reference=y_bounds_reference,
        )
        elem = ti.new_element(**attributes_)
        plem = PaddedText(
            elem, ti.bbox, *ti.padding, ti.line_gap, ti.font_size, metrics
        )
        elems.append(plem)

    font_info.maybe_close()

    if input_one_text_item:
        return elems[0]
    return elems


@overload
def wrap_text_ft(
    font: str | os.PathLike[str],
    text: str,
    width: float,
    font_size: float | None = None,
    ascent: float | None = None,
    descent: float | None = None,
    *,
    y_bounds_reference: str | None = None,
) -> list[str]: ...


@overload
def wrap_text_ft(
    font: str | os.PathLike[str],
    text: list[str],
    width: float,
    font_size: float | None = None,
    ascent: float | None = None,
    descent: float | None = None,
    *,
    y_bounds_reference: str | None = None,
) -> list[list[str]]: ...


def wrap_text_ft(
    font: str | os.PathLike[str],
    text: str | list[str],
    width: float,
    font_size: float | None = None,
    ascent: float | None = None,
    descent: float | None = None,
    *,
    y_bounds_reference: str | None = None,
) -> list[str] | list[list[str]]:
    """Wrap text to fit within the width of the font's bounding box."""
    input_one_text_item = False
    if isinstance(text, str):
        input_one_text_item = True
        text = [text]

    all_wrapped: list[list[str]] = []
    font_info = FTFontInfo(font)

    def get_width(line: str) -> float:
        ti = get_padded_text_info(
            font_info,
            line,
            font_size,
            ascent,
            descent,
            y_bounds_reference=y_bounds_reference,
        )
        return ti.bbox.width

    try:
        for text_item in text:
            words = text_item.split()
            if not words:
                all_wrapped.append([])
                continue
            wrapped: list[str] = [words.pop(0)]
            while words:
                next_word = words.pop(0)
                test_line = f"{wrapped[-1]} {next_word}"
                if get_width(test_line) <= width:
                    wrapped[-1] = test_line
                else:
                    wrapped.append(next_word)
            all_wrapped.append(wrapped)
    finally:
        font_info.font.close()
    if input_one_text_item:
        return all_wrapped[0]
    return all_wrapped
