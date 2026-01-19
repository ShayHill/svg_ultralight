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
    tspans_ = [x for x in tspans if x.text]
    for left, right in it.pairwise(tspans_):
        advance = _get_inner_text_advance(font, left.text[-1], right.text[0])
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
    non_empty = [x for x in tspans if x.text]

    if not non_empty:
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
