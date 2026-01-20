"""Test justification functions.

:author: Shay Hill
:created: 2026-01-19
"""

# pyright: reportPrivateUsage=false

from pathlib import Path

from paragraphs import par

from svg_ultralight.font_tools.align_text import hyphenate_text, justify, justify_text

PARAGRAPH = par(
    """When the wind was in the east, a smell came across the harbour from the shark 
    factory; but today there was only the faint edge of the odour, because the wind had
    backed into the north and then dropped off and it was pleasant and sunny on the
    Terrace."""
)

FONT = Path("C:/Windows/Fonts/BOOKOS.TTF")

PLEMS = hyphenate_text(FONT, PARAGRAPH)


class TestJustification:
    def test_justify_text_with_font_size(self) -> None:
        """Test justify_text with font_size scaling."""
        expect = [
            ["When", "the", "wind", "was"],
            ["in", "the", "east,", "a"],
            ["smell", "came", "across"],
            ["the", "harbour", "from"],
            ["the", "shark", "factory;"],
            ["but", "today", "there"],
            ["was", "only", "the"],
            ["faint", "edge", "of", "the"],
            ["odour,", "because", "the"],
            ["wind", "had", "backed"],
            ["into", "the", "north"],
            ["and", "then", "dropped"],
            ["off", "and", "it", "was"],
            ["pleasant", "and", "sunny"],
            ["on", "the", "Terrace."],
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
            ["into", "the", "north", "and"],
            ["then", "dropped", "off", "and"],
            ["it", "was", "pleasant", "and"],
            ["sunny", "on", "the", "Terrace."],
        ]
        result = justify_text(FONT, PARAGRAPH, 24000, hyphenation_penalty=0.0)
        assert result == expect

    def test_high_penalty(self) -> None:
        expect = [
            ["When", "the", "wind", "was", "in"],
            ["the", "east,", "a", "smell", "came"],
            ["across", "the", "harbour"],
            ["from", "the", "shark", "factory;"],
            ["but", "today", "there", "was"],
            ["only", "the", "faint", "edge"],
            ["of", "the", "odour,", "because"],
            ["the", "wind", "had", "backed"],
            ["into", "the", "north", "and"],
            ["then", "dropped", "off", "and"],
            ["it", "was", "pleasant", "and"],
            ["sunny", "on", "the", "Terrace."],
        ]
        result = justify_text(FONT, PARAGRAPH, 24000, hyphenation_penalty=1)
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
            ["Ter-"], ["race."],
        ]
        # fmt: on
        result = justify_text(FONT, PARAGRAPH, 5000, hyphenation_penalty=0.1)
        assert result == expect
