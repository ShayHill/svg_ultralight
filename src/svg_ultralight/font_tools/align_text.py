"""Functions for aligning and wrapping text using font information.

:author: Shay Hill
:created: 2025-01-15
"""

from __future__ import annotations

import functools
import itertools as it
import os
from typing import TYPE_CHECKING, TypeAlias, overload

from svg_ultralight.bounding_boxes.type_padded_text import (
    PaddedText,
    new_padded_union,
)
from svg_ultralight.font_tools.font_info import (
    DATA_TEXT_ESCAPE_CHARS,
    FTFontInfo,
    FTTextInfo,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )

    from svg_ultralight.attrib_hints import ElemAttrib

FontArg: TypeAlias = str | os.PathLike[str] | FTFontInfo


def _desanitize_svg_data_text(text: str) -> str:
    """Desanitize a string from an SVG data-text attribute.

    :param text: The input string to desanitize.
    :return: The desanitized string with XML characters unescaped.
    """
    for char, escape_seq in DATA_TEXT_ESCAPE_CHARS.items():
        text = text.replace(escape_seq, char)
    return text


def _iter_chars(tspan: PaddedText) -> Iterator[EtreeElement]:
    """Iterate over the characters in a PaddedText element.

    :param tspan: The PaddedText element to iterate over.
    :return: An iterator over the characters in the PaddedText element.
    """
    for child in tspan.elem.iter():
        if child.tag != "path":
            continue
        if not child.attrib.get("data-text"):
            continue
        yield child


def _has_chars(tspan: PaddedText) -> bool:
    """Check if a PaddedText element has characters.

    :param tspan: The PaddedText element to check.
    :return: True if the element has characters, False otherwise.
    """
    try:
        _ = next(_iter_chars(tspan))
    except StopIteration:
        return False
    else:
        return True


@functools.lru_cache
def _get_inner_text_advance(font: FontArg, *chars: str) -> float:
    """Get the spacing b/t the first and last characters.

    :param font: the font to use.
    :param chars: the characters to get the spacing for.
    :return: the spacing the left side of the first character and the rigth side of the
        last character.

    The purpose of this function is to measure the distance between two consecutive text
    spans, perhaps adding intermendiate characters (a space).

    `_get_inner_text_advance(font, "a", "b")`
    would be the distance between a and b in "ab".
    `_get_inner_text_advance(font, "a", " ", "b")`
    would be the distance between a and b in "a b".
    """
    font_info = FTFontInfo(font)
    names = [font_info.try_glyph_name(c) for c in chars]
    spaces = [font_info.kern_table.get((a, b), 0) for a, b in it.pairwise(names)]
    middle_chars = [font_info.get_char_bbox(c).width for c in chars[1:-1]]
    return sum(spaces) + sum(middle_chars)


def _get_space_between_two_text_spans(
    font: FontArg, left: PaddedText, right: PaddedText
) -> float:
    """Get the spacing b/t last character of left and first character of right."""
    l_joint = list(_iter_chars(left))[-1].attrib["data-text"]
    l_joint = _desanitize_svg_data_text(l_joint)
    r_joint = next(_iter_chars(right)).attrib["data-text"]
    r_joint = _desanitize_svg_data_text(r_joint)
    return _get_inner_text_advance(font, l_joint, r_joint)


def align_tspans(font: FontArg, *tspans: PaddedText) -> None:
    """Arrange multiple PaddedText elements as if they were one long string.

    :param font: the one font file used for kerning.
    :param tspans: variable number of tspan elements (each a group element of
        path elements) to join (each an output from pad_text).

    This is limited and will not handle arbitrary text elements (only `g` elements
    with a "data-text" attribute equal to the character(s) in the tspan). Will also
    not handle scaled PaddedText instances. This is for joining tspans immediately
    after they are created and all using similar fonts.
    """
    tspans_ = [x for x in tspans if _has_chars(x)]
    for left, right in it.pairwise(tspans_):
        advance = _get_space_between_two_text_spans(font, left, right)
        if advance:
            advance *= (left.scale[0] + right.scale[0]) / 2
        right.x = left.x2 + advance


def join_tspans(
    font: FontArg, *tspans: PaddedText, **attributes: ElemAttrib
) -> PaddedText:
    """Join multiple PaddedText elements as if they were one long string.

    :param font: the one font file used for kerning.
    :param tspans: list of tspan elements to join (each an output from pad_chars_ft).

    This is limited and will not handle arbitrary text elements (only `g` elements
    with a "data-text" attribute equal to the character(s) in the tspan).
    """
    non_empty = list(filter(_has_chars, tspans))

    if not non_empty:
        # If all tspans are empty, return the first
        if tspans:
            return new_padded_union(*tspans[:1], **attributes)
        msg = "Cannot join empty tspans."
        raise ValueError(msg)

    align_tspans(font, *non_empty)
    return new_padded_union(*non_empty, **attributes)


def _wrap_one_text(font: FontArg, text: str, width: float) -> list[str]:
    """Wrap one line of text.

    :param font: path to a font file or an FTFontInfo instance
    :param text: the text string to wrap
    :param width: the maximum width for the line
    :return: a list of wrapped lines
    """
    words = list(filter(None, (x.strip() for x in text.split())))
    if not words:
        return []
    lines = [words[0]]
    for next_word in words[1:]:
        line_plus_word = f"{lines[-1]} {next_word}"
        if FTTextInfo(font, line_plus_word).bbox.width > width:
            lines.append(next_word)
            continue
        lines[-1] = line_plus_word
    return lines


@overload
def wrap_text(
    font: FontArg, text: str, width: float, font_size: float | None = None
) -> list[str]: ...


@overload
def wrap_text(
    font: FontArg, text: list[str], width: float, font_size: float | None = None
) -> list[list[str]]: ...


def wrap_text(
    font: FontArg, text: str | list[str], width: float, font_size: float | None = None
) -> list[str] | list[list[str]]:
    """Wrap text to fit within the specified width.

    :param font: path to a font file or an FTFontInfo instance
    :param text: the text string(s) to wrap.
    :param width: the maximum width for each line. This width is used to
        determine where line breaks should occur based on the font's text
        metrics.
    :param font_size: optional font size to scale the width calculation. If
        provided, the width is scaled relative to the font's units_per_em. If
        None, uses the font's native size.
    :return: If text is a string, returns a list of strings (wrapped lines).
        If text is a list of strings, returns a list of lists of strings
        (wrapped lines for each input string).
    """
    scale = font_size / FTFontInfo(font).units_per_em if font_size else 1.0
    width /= scale
    if isinstance(text, str):
        return _wrap_one_text(font, text=text, width=width)
    return [_wrap_one_text(font, x, width) for x in text]
