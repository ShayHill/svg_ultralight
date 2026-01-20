"""Test justification functions.

:author: Shay Hill
:created: 2026-01-19
"""

import itertools as it
import string
import uuid
from pathlib import Path

import pyphen
from paragraphs import par

import svg_ultralight.font_tools.align_text as mod
from svg_ultralight.bounding_boxes.padded_text_initializers import pad_text
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText

# pyright: reportPrivateUsage=false

PARAGRAPH = par(
    """The quick brown fox jumps over the lazy dog. This sentence contains every letter 
    of the alphabet and serves as a useful test for typography and text rendering. When
    designing fonts or testing text layout algorithms, it is important to have sample
    text that exercises  all characters. The fox and dog provide a memorable framework
    for this purpose, while also demonstrating how different letter combinations can
    create visual rhythm and balance in written text."""
)


HYP = str(uuid.uuid4())
FONT = Path("C:/Windows/Fonts/bahnschrift.ttf")


def split_word(word: str) -> list[str]:
    """Split a word with hyphenation, preserving leading and trailing punctuation.

    :param word: The word to split
    :return: List of word parts after hyphenation
    """
    beg_punct = "".join(it.takewhile(lambda x: x in string.punctuation, word))
    end_punct = "".join(it.takewhile(lambda x: x in string.punctuation, reversed(word)))
    word_core = word[len(beg_punct) : -len(end_punct)]
    parts = pyphen.Pyphen(lang="en_US").inserted(word_core, hyphen=HYP).split(HYP)
    parts[0] = beg_punct + parts[0]
    parts[-1] = parts[-1] + end_punct
    if len(parts) == 1:
        return [word]
    print(parts)
    return parts


PLEMS: list[PaddedText] = []
for word in PARAGRAPH.split():
    split = split_word(word)
    if len(split) > 1:
        tag = str(uuid.uuid4())
        new_plems = pad_text(FONT, split)
        for plem in new_plems[:-1]:
            plem.tag = tag
        new_plems[-1].tag = f"{tag};END"
        PLEMS.extend(new_plems)
    else:
        PLEMS.append(pad_text(FONT, word))

    # if len(split) > 1:
    #     WORDS.extend([x + HYP for x in split[:-1]])
    #     WORDS.append(split[-1])
    # else:
    #     WORDS.append(word)


# PLEMS = pad_text(FONT, WORDS)


class TestJustification:
    def test_build_next_line(self) -> None:
        mod.justify(FONT, PLEMS, 20000)
