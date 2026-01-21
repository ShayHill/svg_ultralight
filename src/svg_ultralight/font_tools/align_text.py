"""Functions for aligning and wrapping text using font information.

This module provides functions for text layout operations including:
- Aligning and joining text spans with proper kerning
- Wrapping text to fit within specified widths
- Justifying text with optimal line breaks
- Hyphenating words for better text flow

:author: Shay Hill
:created: 2026-01-19
"""

from __future__ import annotations

import functools
import itertools as it
import os
import string
import uuid
from typing import TYPE_CHECKING, NamedTuple, TypeAlias, overload

import pyphen

from svg_ultralight.bounding_boxes.padded_text_initializers import pad_text
from svg_ultralight.bounding_boxes.type_padded_text import (
    PaddedText,
    new_padded_union,
)
from svg_ultralight.font_tools.font_info import (
    FTFontInfo,
)

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from svg_ultralight.attrib_hints import ElemAttrib

hyphenator = pyphen.Pyphen(lang="en_US")

FontArg: TypeAlias = str | os.PathLike[str] | FTFontInfo


# Cost == inf is used to signify that a line is too wide and therefore there is no
# solution to be found by adding more words. _ALMOST_INF is a very strong penalty that
# does not trigger that mechanism.
_INF = float("inf")
_ALMOST_INF = 2**32

# Hyphenation penalty is a scalar for line length. A value of 0.0 means no penalty. A
# value of _INF means hyphenation is not allowed unless a single word exceeds
# the line width. A value of 1.0 means a penalty of the entire line width, so a strong
# penalty.
_DEFAULT_HYPENATION_PENALTY = 0.1


# ============================================================================
# Low-level helper functions
# ============================================================================


@functools.lru_cache
def _get_inner_text_advance(font: FontArg, *chars: str) -> float:
    """Get the spacing between the first and last characters.

    :param font: the font to use
    :param chars: the characters to get the spacing for
    :return: the spacing between the left side of the first character and the right side
        of the last character

    The purpose of this function is to measure the distance between two consecutive text
    spans, perhaps adding intermediate characters (a space).

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


def split_word(word: str) -> list[str]:
    """Split a word with hyphenation, preserving leading and trailing punctuation.

    :param word: the word to split
    :return: list of word parts after hyphenation. If the word cannot be hyphenated,
        returns a list containing the original word
    """
    hyp_delimiter = str(uuid.uuid4())
    beg_punct = "".join(it.takewhile(lambda x: x in string.punctuation, word))
    end_punct = "".join(it.takewhile(lambda x: x in string.punctuation, reversed(word)))
    word_core = word[len(beg_punct) : len(word) - len(end_punct)]
    parts = hyphenator.inserted(word_core, hyphen=hyp_delimiter).split(hyp_delimiter)
    if len(parts) == 1:
        return [word]
    parts[0] = beg_punct + parts[0]
    parts[-1] = parts[-1] + end_punct
    return parts


def _hyphenated_word_group(word: PaddedText) -> str:
    """Get the hyphenation group tag for a word.

    :param word: the PaddedText instance to get the group tag from
    :return: the hyphenation group tag (the part before the semicolon in the tag)
    """
    return word.tag.split(";")[0]


# ============================================================================
# Hyphenation functions
# ============================================================================


def hyphenate(plem: PaddedText) -> list[PaddedText]:
    """Hyphenate a PaddedText instance, splitting it into multiple parts if possible.

    :param plem: the PaddedText instance to hyphenate
    :return: list of PaddedText instances. If the word cannot be split, returns a list
        containing the original PaddedText. Split parts are tagged with a common UUID
        to allow rejoining later
    """
    split = split_word(plem.text)
    if len(split) == 1:
        return [plem]

    tag = str(uuid.uuid4())
    new_plems = [plem.with_text(text) for text in split]
    for new_plem in new_plems[:-1]:
        new_plem.tag = tag
    new_plems[-1].tag = f"{tag};END"
    return new_plems


def hyphenate_text(font: FontArg, text: str) -> list[PaddedText]:
    """Hyphenate text by splitting words and creating PaddedText instances.

    :param font: the font to use
    :param text: the text string to hyphenate
    :return: list of PaddedText instances with hyphenated words split
    """
    plems = pad_text(font, text.split())
    return list(it.chain(*(hyphenate(p) for p in plems)))


def _join_hyphenated_words(words: Sequence[PaddedText]) -> list[PaddedText]:
    """Join hyphenated word parts back into complete words.

    :param words: sequence of PaddedText instances, some of which may be parts of
        hyphenated words
    :return: list of PaddedText instances with hyphenated parts rejoined. Words that
        were split are rejoined, and a hyphen is added if the word was split mid-line
    """
    words_: list[PaddedText] = []
    last_key = _hyphenated_word_group(words[-1])
    grouped = it.groupby(words, _hyphenated_word_group)
    for key, group in grouped:
        group_ = tuple(group)
        if not key:
            words_.extend(group_)
            continue
        text = "".join(x.text for x in group_)
        if (
            key == last_key
            and not words[-1].tag.endswith("END")
            and words[-1].text[-1] != "-"
        ):
            text += "-"
        words_.append(group_[0].with_text(text))
    return words_


# ============================================================================
# Line breaking internals
# ============================================================================


def _get_word_advances(font: FontArg, *words: PaddedText) -> Iterator[float]:
    """Get the advance width for each word including spacing.

    :param font: the font used for measuring spacing
    :param words: the PaddedText instances to measure
    :return: iterator yielding the advance width for each word. The advance includes the
        word's width plus the spacing to the next word (if any)
    """
    font_path = FTFontInfo(font).path
    for left, right in it.pairwise(words):
        space = _get_inner_text_advance(font_path, left.text[-1], " ", right.text[0])
        space *= (left.scale[0] + right.scale[0]) / 2
        yield left.bbox.width + space
    yield words[-1].bbox.width


def _get_line_cost(
    font: FontArg,
    width: float,
    *words: PaddedText,
    hyp_pen: float | None = None,
) -> float:
    """Get the cost of a line.

    :param font: the font used for measuring word advances
    :param width: the target line width
    :param words: the words on this candidate line
    :param hyp_pen: optional penalty scalar for lines ending with a
        hyphenated word. If None, uses the default hyphenation penalty
    :return: the cost of the line. Lower is better. Returns infinity if the line is too
        wide and cannot fit
    """
    if hyp_pen is None:
        hyp_pen = _DEFAULT_HYPENATION_PENALTY
    if not words:
        msg = "Cannot get the cost of an empty line."
        raise ValueError(msg)
    words_ = _join_hyphenated_words(words)
    advances = list(_get_word_advances(font, *words_))
    total_cost = width - sum(advances)
    if total_cost < 0:
        return _ALMOST_INF - 1 if len(advances) == 1 else _INF
    num_spaces = len(advances) - 1
    if num_spaces == 0:
        cost = total_cost * 2
    elif num_spaces == 1:
        cost = total_cost
    else:
        cost = total_cost / num_spaces
    if words_ and words_[-1].text.endswith("-"):
        cost = min(cost + hyp_pen * width, _ALMOST_INF)
    return pow(cost, 2)


class _LineBreaks(NamedTuple):
    """A candidate sequence of line-break indices.

    :param path: the sequence of line-break indices, always starting with 0.
    :param cost: the cost of the candidate.
    """

    path: tuple[int, ...] = (0,)
    cost: float = 0


def _find_best_line_breaks(
    font: FontArg,
    words: list[PaddedText],
    width: float,
    hyp_pen: float | None = None,
) -> tuple[int, ...]:
    """Find the optimal line-break path for a sequence of words.

    Uses dynamic programming to find the line breaks that minimize total cost.

    :param font: the font used for measuring word advances
    :param words: the words to break into lines
    :param width: the target line width
    :param hyp_pen: optional penalty scalar for lines ending with a
        hyphenated word
    :return: tuple of indices describing optimal line breaks. Each index indicates where
        a new line should start
    """
    heads = [
        _LineBreaks((0,), 0),
        *(_LineBreaks((0, x + 1), _INF) for x in range(len(words))),
    ]
    for beg in range(len(words)):
        for end in range(beg + 1, len(words) + 1):
            cost = _get_line_cost(font, width, *words[beg:end], hyp_pen=hyp_pen)
            if cost == _INF:
                break
            if end == len(words):
                cost = 0
            cost += heads[beg].cost
            candidate = _LineBreaks((*heads[beg].path, end), cost)
            if candidate.cost < heads[end].cost:
                heads[end] = candidate
    return heads[-1].path


def _iter_joined_hyphenations(
    words: list[PaddedText], path: tuple[int, ...]
) -> Iterator[list[PaddedText]]:
    """Iterate over lines with hyphenated words joined.

    :param words: the list of PaddedText instances (may include hyphenated parts)
    :param path: tuple of indices indicating line breaks
    :return: iterator yielding lists of PaddedText instances, one per line, with
        hyphenated word parts rejoined
    """
    for beg, end in it.pairwise(path):
        yield _join_hyphenated_words(words[beg:end])


def _construct_hyphenated_text_lines(
    font: FontArg,
    words: list[PaddedText],
    width: float,
    path: tuple[int, ...],
    *,
    justify: bool,
) -> list[list[PaddedText]]:
    """Translate path words into justified lines.

    :param font: the font used for measuring word advances
    :param words: the words to justify
    :param width: the target line width
    :param path: the path describing line breaks
    :param justify: if True, distribute space between words to justify lines. The last
        line is not justified
    :return: list of lists of PaddedText instances, one list per line
    """
    lines = list(_iter_joined_hyphenations(words, path))
    for line_idx, line in enumerate(lines):
        advances = list(_get_word_advances(font, *line))
        if justify:
            is_last_line = line_idx == len(lines) - 1
            spaces = len(advances) - 1
            if spaces:
                if not is_last_line:
                    part_cost = (width - sum(advances)) / spaces
                    advances[:-1] = (x + part_cost for x in advances[:-1])
                for j in range(1, len(advances)):
                    line[j].x += sum(advances[:j])
    return lines


# ============================================================================
# Public API functions
# ============================================================================


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
    font_path = FTFontInfo(font).path
    for left, right in it.pairwise(tspans_):
        advance = _get_inner_text_advance(font_path, left.text[-1], right.text[0])
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


def justify_text(
    font: FontArg,
    text: str,
    width: float,
    font_size: float | None = None,
    hyp_pen: float | None = None,
) -> list[list[str]]:
    """Justify text and return lines as lists of words.

    :param font: the font used for measuring word advances
    :param text: the text string to justify
    :param width: the target line width
    :param font_size: optional font size to scale the width calculation. If
        provided, the width is scaled relative to the font's units_per_em. If
        None, uses the font's native size.
    :param hyp_pen: optional penalty scalar for lines ending with a
        hyphenated word. If None, no additional penalty is applied.
    :return: list of lists of strings, where each inner list represents a line
        with words as separate strings
    """
    scale = font_size / FTFontInfo(font).units_per_em if font_size else 1.0
    width /= scale
    words = hyphenate_text(font, text)
    path = _find_best_line_breaks(font, words, width, hyp_pen)
    plemss = _iter_joined_hyphenations(words, path)
    return [[word.text for word in line] for line in plemss]


@overload
def wrap_text(
    font: FontArg,
    text: str,
    width: float,
    font_size: float | None = None,
    hyp_pen: float | None = None,
) -> list[str]: ...


@overload
def wrap_text(
    font: FontArg,
    text: list[str],
    width: float,
    font_size: float | None = None,
    hyp_pen: float | None = None,
) -> list[list[str]]: ...


def wrap_text(
    font: FontArg,
    text: str | list[str],
    width: float,
    font_size: float | None = None,
    hyp_pen: float | None = _INF,
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
    :param hyp_pen: optional penalty scalar for lines ending with a
        hyphenated word. If None, defaults to _INF to prevent
        hyphenation unless a single word exceeds the line width.
    :return: If text is a string, returns a list of strings (wrapped lines).
        If text is a list of strings, returns a list of lists of strings
        (wrapped lines for each input string).
    """
    if hyp_pen is None:
        hyp_pen = _INF
    if isinstance(text, str):
        lines = justify_text(font, text, width, font_size, hyp_pen)
        return [" ".join(line) for line in lines]
    return [
        [" ".join(line) for line in justify_text(font, t, width, font_size, hyp_pen)]
        for t in text
    ]


def justify(
    font: FontArg,
    words: list[PaddedText],
    width: float,
    hyp_pen: float | None = None,
) -> list[list[PaddedText]]:
    """Justify text and write to SVG file.

    :param font: the font used for measuring word advances
    :param words: padded words to justify
    :param width: the target line width
    :param hyp_pen: optional penalty scalar for lines ending with a
        hyphenated word. If None, no additional penalty is applied
    :return: list of strings, one per justified line. Also writes the justified text
        to "temp.svg" as a side effect
    """
    path = _find_best_line_breaks(font, words, width, hyp_pen)
    return _construct_hyphenated_text_lines(font, words, width, path, justify=True)


def wrap(
    font: FontArg,
    words: list[PaddedText],
    width: float,
    hyp_pen: float | None = None,
) -> list[list[PaddedText]]:
    """Wrap text into lines without justification.

    :param font: the font used for measuring word advances
    :param words: padded words to wrap
    :param width: the target line width
    :param hyp_pen: optional penalty scalar for lines ending with a
        hyphenated word. If None, no additional penalty is applied
    :return: list of lists of PaddedText instances, one list per wrapped line
    """
    path = _find_best_line_breaks(font, words, width, hyp_pen)
    return _construct_hyphenated_text_lines(font, words, width, path, justify=False)
