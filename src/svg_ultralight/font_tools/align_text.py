"""Functions for aligning and wrapping text using font information.

:author: Shay Hill
:created: 2025-01-15
"""

from __future__ import annotations

import copy


import dataclasses
import functools
import itertools as it
import os
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, NamedTuple, TypeAlias, overload

import pyphen

from svg_ultralight.bounding_boxes.type_padded_list import PaddedList
from svg_ultralight.bounding_boxes.type_padded_text import (
    PaddedText,
    new_padded_union,
)
from svg_ultralight.font_tools.font_info import (
    FTFontInfo,
    FTTextInfo,
)
from svg_ultralight.main import write_svg
from svg_ultralight.root_elements import new_svg_root_around_bounds

if TYPE_CHECKING:
    from svg_ultralight.attrib_hints import ElemAttrib

hyphenator = pyphen.Pyphen(lang="en_US")

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
    if len(chars) < 2:
        return 0
    font_info = FTFontInfo(font)

    names = [font_info.try_glyph_name(c) for c in chars]
    l_hmtx = font_info.hmtx[names[0] or "space"]
    l_adv = l_hmtx[0] - l_hmtx[1]
    r_adv = font_info.get_char_bbox(chars[-1]).x2
    min_x, _, max_x, _ = font_info.get_text_bounds("".join(chars))
    return max_x - min_x - l_adv - r_adv


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


def _get_word_advances(font: FontArg, *words: PaddedText) -> Iterator[float]:
    """Get the advance for each word."""
    for left, right in it.pairwise(words):
        space = _get_inner_text_advance(font, left.text[-1], " ", right.text[0])
        yield left.bbox.width + space
    yield words[-1].bbox.width


def _hyphenated_word_group(word: PaddedText) -> str:
    return word.tag.split(";")[0]


def _join_hyphenated_words(
    words: Sequence[PaddedText],
) -> list[PaddedText | FTTextInfo]:
    """Join hyphenated words into a single word."""
    words_: list[PaddedText | FTTextInfo] = []
    last_key = _hyphenated_word_group(words[-1])
    grouped = it.groupby(words, _hyphenated_word_group)
    for key, group in grouped:
        if not key:
            words_.extend(group)
            continue
        group_ = tuple(group)
        font = group_[0].font
        text = "".join(x.text for x in group_)
        if key == last_key and not words[-1].tag.endswith("END"):
            text += "-"
        words_.append(FTTextInfo(font, text))
    return words_


def _get_line_cost(font: FontArg, width: float, *words: PaddedText) -> float:
    """Get the cost of a line."""
    if not words:
        msg = "Cannot get the cost of an empty line."
        raise ValueError(msg)
    words_ = _join_hyphenated_words(words)
    advances = list(_get_word_advances(font, *words_))
    total_cost = width - sum(advances)
    if total_cost < 0:
        return 0 if len(advances) == 1 else float("inf")
    if len(advances) == 1:
        return pow(total_cost * 2, 2)
    if len(advances) == 2:
        return pow(total_cost, 2)
    return pow(total_cost / (len(advances) - 1), 2)


class CandidateLineBreakIndices(NamedTuple):
    """A candidate sequence of line-break indices.

    :param path: the sequence of line-break indices, always starting with 0.
    :param cost: the cost of the candidate.
    """

    path: tuple[int, ...] = (0,)
    cost: float = 0


def _construct_justification(
    font: FontArg, words: list[PaddedText], width: float, path: tuple[int, ...]
) -> list[list[PaddedText]]:
    """Translate path words into a justification."""
    result: list[list[PaddedText]] = []
    for beg, end in it.pairwise(path):
        line = _join_hyphenated_words(words[beg:end])
        plems = [x if isinstance(x, PaddedText) else x.new_padded_text() for x in line]
        advances = list(_get_word_advances(font, *plems))
        full_cost = 0 if end == len(words) else width - sum(advances)
        spaces = len(advances) - 1
        if spaces:
            part_cost = full_cost / spaces
            advances[:-1] = (x + part_cost for x in advances[:-1])
            for i in range(1, len(advances)):
                plems[i].x += sum(advances[:i])
        result.append(plems)
    return result


def justify(
    font: FontArg | Iterable[FontArg], words: list[PaddedText], width: float
) -> list[str]:
    """Justify text."""
    heads = [
        CandidateLineBreakIndices((0,), 0),
        *(
            CandidateLineBreakIndices((0, x + 1), float("inf"))
            for x in range(len(words))
        ),
    ]
    for beg in range(len(words)):
        for end in range(beg + 1, len(words) + 1):
            cost = _get_line_cost(font, width, *words[beg:end])
            if cost == float("inf"):
                break
            if end == len(words) - 1:
                cost = 0
            cost += heads[beg].cost
            candidate = CandidateLineBreakIndices((*heads[beg].path, end), cost)
            if candidate.cost < heads[end].cost:
                heads[end] = candidate
    plemss = _construct_justification(font, words, width, heads[-1].path)
    plems = [new_padded_union(*x) for x in plemss]
    _ = PaddedList(*plems).stack()
    root = new_svg_root_around_bounds(*plems)
    _ = write_svg("temp.svg", root)
    return plems
