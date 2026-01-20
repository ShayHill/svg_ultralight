"""Test justification functions.

:author: Shay Hill
:created: 2026-01-19
"""

# pyright: reportPrivateUsage=false

from pathlib import Path

from paragraphs import par

import svg_ultralight.font_tools.align_text as mod
from svg_ultralight.font_tools.align_text import hyphenate_text

PARAGRAPH = par(
    """When the wind was in the east, a smell came across the harbour from the shark 
    factory; but today there was only the faint edge of the odour, because the wind had
    backed into the north and then dropped off and it was pleasant and sunny on the
    Terrace."""
)

FONT = Path("C:/Windows/Fonts/BOOKOS.TTF")

PLEMS = hyphenate_text(FONT, PARAGRAPH)


# PLEMS: list[PaddedText] = []
# for word in PARAGRAPH.split():
#     split = split_word(word)
#     if len(split) > 1:
#         tag = str(uuid.uuid4())
#         new_plems = pad_text(FONT, split)
#         for plem in new_plems[:-1]:
#             plem.tag = tag
#         new_plems[-1].tag = f"{tag};END"
#         PLEMS.extend(new_plems)
#     else:
#         PLEMS.append(pad_text(FONT, word))

# if len(split) > 1:
#     WORDS.extend([x + HYP for x in split[:-1]])
#     WORDS.append(split[-1])
# else:
#     WORDS.append(word)


# PLEMS = pad_text(FONT, WORDS)


import time


class TestJustification:
    def test_build_next_line(self) -> None:
        beg = time.time()
        mod.justify(FONT, PLEMS, 24000, hyphenation_penalty=0.1)
        end = time.time()
        print(f"Time taken: {end - beg} seconds")
