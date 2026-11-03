"""Test justification functions.

:author: Shay Hill
:created: 2026-01-19
"""

from pathlib import Path

from paragraphs import par

from svg_ultralight.bounding_boxes.padded_text_initializers import pad_text
from svg_ultralight.font_tools.align_text import (
    _find_best_line_breaks,
    hyphenate_text,
    justify,
    justify_text,
    wrap,
    wrap_text,
)

PARAGRAPH = par(
    """When the wind was in the east, a smell came across the harbour from the shark
    factory; but today there was only the faint edge of the odour, because the wind had
    backed into the north and then dropped off and it was pleasant and sunny on the
    Terrace."""
)

FONT = Path("C:/Windows/Fonts/BOOKOS.TTF")

PLEMS = hyphenate_text(FONT, PARAGRAPH)


class TestJustification:
    def test_include_last_line_cost(self) -> None:
        """Optionally include the final line in the break cost."""
        words = hyphenate_text(FONT, "one two three four five six seven eight nine ten")

        assert _find_best_line_breaks(FONT, words, 10000) == (0, 2, 4, 6, 8, 10, 11)
        assert _find_best_line_breaks(
            FONT, words, 10000, include_last_line_cost=True
        ) == (0, 2, 3, 5, 7, 9, 11)

    def test_public_include_last_line_cost(self) -> None:
        """Public text layout APIs forward the final-line cost option."""
        text = "one two three four five six seven eight nine ten"
        justified = [
            ["one", "two"],
            ["three"],
            ["four", "five"],
            ["six", "sev-"],
            ["en", "eight"],
            ["nine", "ten"],
        ]
        wrapped = ["one two", "three four", "five six", "seven", "eight", "nine ten"]

        assert justify_text(FONT, text, 10000, include_last_line_cost=True) == justified
        assert wrap_text(FONT, text, 10000, include_last_line_cost=True) == wrapped
        assert wrap_text(FONT, [text], 10000, include_last_line_cost=True) == [wrapped]
        assert [
            [word.text for word in line]
            for line in justify(
                FONT, hyphenate_text(FONT, text), 10000, include_last_line_cost=True
            )
        ] == justified
        assert [
            [word.text for word in line]
            for line in wrap(
                FONT, hyphenate_text(FONT, text), 10000, include_last_line_cost=True
            )
        ] == justified

    def test_justify_text_with_font_size(self) -> None:
        """Test justify_text with font_size scaling."""
        expect = [
            ["When", "the", "wind", "was"],
            ["in", "the", "east,", "a"],
            ["smell", "came", "across"],
            ["the", "harbour", "from"],
            ["the", "shark", "factory;"],
            ["but", "today", "there"],
            ["was", "only", "the", "faint"],
            ["edge", "of", "the", "odour,"],
            ["because", "the", "wind"],
            ["had", "backed", "into"],
            ["the", "north", "and", "then"],
            ["dropped", "off", "and", "it"],
            ["was", "pleasant", "and"],
            ["sunny", "on", "the", "Ter-"],
            ["race."],
        ]
        result = justify_text(FONT, PARAGRAPH, 5000, font_size=500)
        assert result == expect

    def test_no_penalty(self) -> None:
        expect = [
            ["When", "the", "wind", "was"],
            ["in", "the", "east,", "a", "smell"],
            ["came", "across", "the", "har-"],
            ["bour", "from", "the", "shark"],
            ["factory;", "but", "today", "there"],
            ["was", "only", "the", "faint", "edge"],
            ["of", "the", "odour,", "because"],
            ["the", "wind", "had", "backed"],
            ["into", "the", "north", "and", "then"],
            ["dropped", "off", "and", "it", "was"],
            ["pleasant", "and", "sunny", "on"],
            ["the", "Terrace."],
        ]
        result = justify_text(FONT, PARAGRAPH, 24000, hyp_pen=0.0)
        assert result == expect

    def test_high_penalty(self) -> None:
        expect = [
            ["When", "the", "wind", "was", "in"],
            ["the", "east,", "a", "smell", "came"],
            ["across", "the", "harbour"],
            ["from", "the", "shark", "factory;"],
            ["but", "today", "there", "was"],
            ["only", "the", "faint", "edge", "of"],
            ["the", "odour,", "because", "the"],
            ["wind", "had", "backed", "into"],
            ["the", "north", "and", "then"],
            ["dropped", "off", "and", "it", "was"],
            ["pleasant", "and", "sunny", "on"],
            ["the", "Terrace."],
        ]
        result = justify_text(FONT, PARAGRAPH, 24000, hyp_pen=1)
        assert result == expect

    def test_justify_text_small_width(self) -> None:
        """Test justify_text with a small width produces multiple lines."""
        # fmt: off
        expect = [
            ["When"], ["the"], ["wind"], ["was"], ["in"], ["the"], ["east,"], ["a"],
            ["smell"], ["came"], ["across"], ["the"], ["har-"], ["bour"], ["from"],
            ["the"], ["shark"], ["fac-"], ["tory;"], ["but"], ["to-"], ["day"],
            ["there"], ["was"], ["only"], ["the"], ["faint"], ["edge"], ["of"], ["the"],
            ["odour,"], ["because"], ["the"], ["wind"], ["had"], ["backed"], ["into"],
            ["the"], ["north"], ["and"], ["then"], ["dropped"], ["off"], ["and"],
            ["it"], ["was"], ["pleasant"], ["and"], ["sun-"], ["ny"], ["on"], ["the"],
            ["Terrace."],
        ]
        # fmt: on
        result = justify_text(FONT, PARAGRAPH, 5000, hyp_pen=0.1)
        assert result == expect

    def test_justify_multiple_widths(self) -> None:
        """Test justify_text with multiple widths."""
        expect = [
            ["When", "the"],
            ["wind", "was", "in", "the", "east,", "a"],
            ["smell", "came"],
            ["across", "the", "harbour"],
            ["from", "the"],
            ["shark", "factory;", "but"],
            ["today", "there"],
            ["was", "only", "the", "faint"],
            ["edge", "of", "the"],
            ["odour,", "because", "the"],
            ["wind", "had"],
            ["backed", "into", "the", "north"],
            ["and", "then"],
            ["dropped", "off", "and", "it"],
            ["was", "pleas-"],
            ["ant", "and", "sunny", "on", "the"],
            ["Terrace."],
        ]
        result = justify_text(FONT, PARAGRAPH, [12000, 24000] * 50, hyp_pen=0.1)
        assert result == expect

    def test_justify(self) -> None:
        """Smoke test justify function."""
        words = [pad_text(FONT, word) for word in PARAGRAPH.split()]
        result = justify(FONT, words, [12000, 24000] * 50, hyp_pen=0.1)
        assert len(result) == 17
