"""Functions that create PaddedText instances.

Three variants:

- `pad_text_inkscape`: uses Inkscape to measure text bounds

- `pad_text`: uses fontTools to measure text bounds (faster, and you get line_gap)

There is a default font size for pad_text_inkscape if an element is passed. There is
also a default for the other pad_text_ functions, but it taken from the font file and
is usually 1024, so it won't be easy to miss. The default for standard
pad_text_inkscape is to prevent surprises if Inksape defaults to font-size 12pt while
your browser defaults to 16px.

:author: Shay Hill
:created: 2025-06-09
"""

from __future__ import annotations

import copy
import itertools as it
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
    FTTextInfo,
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

# A default font size for pad_text_inkscape if font-size is not specified in the
# reference element.
DEFAULT_FONT_SIZE_FOR_PAD_TEXT = 12.0  # Default font size for pad_text_inkscape


def _desanitize_svg_data_text(text: str) -> str:
    """Desanitize a string from an SVG data-text attribute.

    :param text: The input string to desanitize.
    :return: The desanitized string with XML characters unescaped.
    """
    for char, escape_seq in DATA_TEXT_ESCAPE_CHARS.items():
        text = text.replace(escape_seq, char)
    return text


def pad_text_inkscape(
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
        use it here to compare results between `pad_text_inkscape` and
        `new_padded_text`.
    :return: a PaddedText instance
    """
    if y_bounds_reference is None:
        y_bounds_reference = DEFAULT_Y_BOUNDS_REFERENCE
    if font is not None:
        _ = update_element(text_elem, **get_svg_font_attributes(font))
    if "font-size" not in text_elem.attrib:
        text_elem.attrib["font-size"] = format_number(DEFAULT_FONT_SIZE_FOR_PAD_TEXT)
    rmargin_ref = copy.deepcopy(text_elem)
    capline_ref = copy.deepcopy(text_elem)
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
def pad_text(
    font: str | os.PathLike[str] | FTFontInfo,
    text: str,
    font_size: float | None = None,
    **attributes: ElemAttrib,
) -> PaddedText: ...


@overload
def pad_text(
    font: str | os.PathLike[str] | FTFontInfo,
    text: list[str],
    font_size: float | None = None,
    **attributes: ElemAttrib,
) -> list[PaddedText]: ...


def pad_text(
    font: str | os.PathLike[str] | FTFontInfo,
    text: str | list[str],
    font_size: float | None = None,
    **attributes: ElemAttrib,
) -> PaddedText | list[PaddedText]:
    """Create a new PaddedText instance using fontTools.

    :param font: path to a font file.
    :param text: the text of the text element or a list of text strings.
    :param font_size: the font size to use. Skip for default font size. This can
        always be set later, but the argument is useful if you're working with fonts
        that have different native font sizes (usually 1000, 1024, or 2048).
    """
    attributes_ = _remove_svg_font_attributes(attributes)
    font = font if isinstance(font, FTFontInfo) else FTFontInfo(font)
    metrics = FontMetrics(
        font.units_per_em,
        font.ascent,
        font.descent,
        font.cap_height,
        font.x_height,
        font.line_gap,
    )

    plems: list[PaddedText] = []
    for t in [text] if isinstance(text, str) else text:
        text_info = FTTextInfo(font, t)
        elem = text_info.new_element(**attributes_)
        plem = PaddedText(
            elem, text_info.bbox, *text_info.padding, metrics=copy.copy(metrics)
        )
        if font_size:
            plem.font_size = font_size
        plems.append(plem)
    font.maybe_close()

    if isinstance(text, str):
        return plems[0]
    return plems


@overload
def wrap_text_ft(
    font: str | os.PathLike[str],
    text: str,
    width: float,
    font_size: float | None = None,
) -> list[str]: ...


@overload
def wrap_text_ft(
    font: str | os.PathLike[str],
    text: list[str],
    width: float,
    font_size: float | None = None,
) -> list[list[str]]: ...


def wrap_text_ft(
    font: str | os.PathLike[str],
    text: str | list[str],
    width: float,
    font_size: float | None = None,
) -> list[str] | list[list[str]]:
    """Wrap text to fit within the width of the font's bounding box."""
    input_one_text_item = False
    if isinstance(text, str):
        input_one_text_item = True
        text = [text]

    all_wrapped: list[list[str]] = []
    font_info = FTFontInfo(font)
    scale = font_size / font_info.units_per_em if font_size else 1.0

    def get_width(line: str) -> float:
        ti = FTTextInfo(font_info, line)
        return ti.bbox.width * scale

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
