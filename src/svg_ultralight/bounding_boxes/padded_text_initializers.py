"""Functions that create PaddedText instances.

Two variants:

- `pad_text_inkscape`: uses Inkscape to measure text bounds. This is a legacy
  function and should not be used in new code.

- `pad_text`: uses fontTools to measure text bounds
  (faster, and reveals font metrics)

There is a default font size for pad_text_inkscape if an element is passed. There is
also a default for the other pad_text functions, but it taken from the font file and
is usually 1024, so it won't be easy to miss. The default for standard
pad_text_inkscape is to prevent surprises if Inksape defaults to font-size 12pt while
your browser defaults to 16px.

:author: Shay Hill
:created: 2025-06-09
"""

from __future__ import annotations

import copy
import itertools as it
import os
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Concatenate,
    ParamSpec,
    TypeAlias,
    TypeVar,
    overload,
)

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
    from collections.abc import Callable

    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )

    from svg_ultralight.attrib_hints import ElemAttrib

DEFAULT_Y_BOUNDS_REFERENCE = "{[|gjpqyf"

# A default font size for pad_text_inkscape if font-size is not specified in the
# reference element.
DEFAULT_FONT_SIZE_FOR_PAD_TEXT = 12.0  # Default font size for pad_text_inkscape


P = ParamSpec("P")
R = TypeVar("R")

FontArg: TypeAlias = str | os.PathLike[str] | FTFontInfo


def open_font_info(
    func: Callable[Concatenate[FontArg, P], R],
) -> Callable[Concatenate[FontArg, P], R]:
    """Decorate functions to open and close an FTFontInfo object.

    If an FTFontInfo instance is provided as the first argument, use it directly
    and leave it open. If a string or path is provided instead, create a local
    FTFontInfo instance and close it after use.
    """

    @wraps(func)
    def wrapper(font: FontArg, *args: P.args, **kwargs: P.kwargs) -> R:
        font_info = FTFontInfo(font)
        result = func(font_info, *args, **kwargs)
        if not isinstance(font, FTFontInfo):
            font_info.__close__()
        return result

    return wrapper


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
        This function will attempt a match to svg font attributes that will match that
        font. This is going to conflict with any font-family, font-style, or other
        font-related attributes *except* font-size. You likely want to use `pad_text`
        if you're going to pass a font path, but you can use it here to compare
        results between `pad_text_inkscape` and `pad_text`.
    :return: a PaddedText instance

    This function is inferior to `pad_text` and should not be used in new code.
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
    return PaddedText(text_elem, bbox, tpad, rpad, bpad, lpad)


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


@open_font_info
def align_tspans(font: FontArg, *tspans: PaddedText) -> None:
    """Arrange multiple PaddedText elements as if they were one long string.

    :param font: the one font file used for kerning.
    :param tspans: list of tspan elements to join (each an output from pad_chars_ft).

    This is limited and will not handle arbitrary text elements (only `g` elements
    with a "data-text" attribute equal to the character(s) in the tspan). Will also
    not handle scaled PaddedText instances. This is for joining tspans immediately
    after they are created and all using similar fonts.
    """
    font_info = FTFontInfo(font)
    for left, right in it.pairwise(tspans):
        l_joint = _desanitize_svg_data_text(left.elem.attrib["data-text"])[-1]
        r_joint = _desanitize_svg_data_text(right.elem.attrib["data-text"])[0]
        l_name = font_info.try_glyph_name(l_joint)
        r_name = font_info.try_glyph_name(r_joint)
        kern = 0.0
        if l_name and r_name:
            kern = font_info.kern_table.get((l_name, r_name), 0)
            kern *= (left.scale[0] + right.scale[0]) / 2
        right.x = left.x2 + kern


def join_tspans(
    font: FontArg, *tspans: PaddedText, **attributes: ElemAttrib
) -> PaddedText:
    """Join multiple PaddedText elements as if they were one long string.

    :param font: the one font file used for kerning.
    :param tspans: list of tspan elements to join (each an output from pad_chars_ft).

    This is limited and will not handle arbitrary text elements (only `g` elements
    with a "data-text" attribute equal to the character(s) in the tspan). Will also
    not handle scaled PaddedText instances. This is for joining tspans immediately
    after they are created and all using similar fonts.
    """
    align_tspans(font, *tspans)
    return new_padded_union(*tspans, **attributes)


@overload
@open_font_info
def pad_text(
    font: FontArg, text: str, font_size: float | None = None, **attributes: ElemAttrib
) -> PaddedText: ...


@overload
@open_font_info
def pad_text(
    font: FontArg,
    text: list[str],
    font_size: float | None = None,
    **attributes: ElemAttrib,
) -> list[PaddedText]: ...


@open_font_info
def pad_text(
    font: FontArg,
    text: str | list[str],
    font_size: float | None = None,
    **attributes: ElemAttrib,
) -> PaddedText | list[PaddedText]:
    """Create a new PaddedText instance using fontTools.

    :param font: path to a font file.
    :param text: the text of the text element or a list of text strings.
    :param font_size: the font size to use. Skip for native font size. This can
        always be set later, but the argument is useful if you're working with fonts
        that have different native font sizes (usually 1000, 1024, or 2048).
    """
    attributes_ = _remove_svg_font_attributes(attributes)
    font = FTFontInfo(font)
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
        ti = FTTextInfo(font, t)
        elem = ti.new_element(**attributes_)
        plem = PaddedText(elem, ti.bbox, *ti.padding, metrics=copy.copy(metrics))
        if font_size:
            plem.font_size = font_size
        plems.append(plem)

    if isinstance(text, str):
        return plems[0]
    return plems


@open_font_info
def _wrap_one_text(font: FontArg, text: str, width: float) -> list[str]:
    """Wrap one line of text."""
    words = list(filter(None, (x.strip() for x in text.split())))
    if not words:
        return []
    lines = [words.pop(0)]
    while words:
        next_word = words.pop(0)
        line_plus_word = f"{lines[-1]} {next_word}"
        if FTTextInfo(font, line_plus_word).bbox.width > width:
            lines.append(next_word)
            continue
        lines[-1] = line_plus_word
    return lines


@overload
@open_font_info
def wrap_text(
    font: FontArg, text: str, width: float, font_size: float | None = None
) -> list[str]: ...


@overload
@open_font_info
def wrap_text(
    font: FontArg, text: list[str], width: float, font_size: float | None = None
) -> list[list[str]]: ...


@open_font_info
def wrap_text(
    font: FontArg, text: str | list[str], width: float, font_size: float | None = None
) -> list[str] | list[list[str]]:
    """Wrap text to fit within the width of the font's bounding box."""
    scale = font_size / FTFontInfo(font).units_per_em if font_size else 1.0
    width /= scale
    if isinstance(text, str):
        return _wrap_one_text(font, text=text, width=width)
    return [_wrap_one_text(font, x, width) for x in text]
