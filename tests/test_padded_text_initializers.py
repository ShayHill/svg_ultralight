"""Test padded_text_initializers.py

:author: Shay Hill
:created: 2025-06-09
"""

import math
from pathlib import Path

import pytest
from conftest import INKSCAPE, has_inkscape

from svg_ultralight.bounding_boxes.padded_text_initializers import (
    join_tspans,
    pad_text,
    pad_text_inkscape,
    wrap_text_ft,
)
from svg_ultralight.constructors import new_element


class TestPadText:
    @pytest.mark.skipif(not has_inkscape(INKSCAPE), reason="Inkscape not found")
    def test_font_arg(self) -> None:
        """Test to see that the font specification does *something*."""
        font = Path("C:/Windows/Fonts/bahnschrift.ttf")
        if not font.exists():
            msg = "Test font file does not exist on system."
            pytest.skip(msg)
        test_elem = new_element("text", text="Lorem ipsum dolor", font_size=12)
        no_font = pad_text_inkscape(INKSCAPE, test_elem)
        with_font = pad_text_inkscape(INKSCAPE, test_elem, font=font)
        assert no_font.bbox.height != with_font.bbox.height


def _random_string(length: int) -> str:
    """Generate a random string of fixed length."""
    import random
    import string

    letters = string.ascii_letters + string.digits + " "
    return "".join(random.choice(letters) for _ in range(length))


class TestPadTextFt:
    def test_join_tspan(self) -> None:
        """Test pad_text with a font file."""
        font = Path("C:/Windows/Fonts/bahnschrift.ttf")
        if not font.exists():
           msg = "Test font file does not exist on system."
           pytest.skip(msg)
        words = [_random_string(5) for _ in range(50)]
        words.append("".join(words))
        plems = pad_text(font, words)
        joined = join_tspans(font, plems[:-1])
        assert joined.width == plems[-1].width

    def test_do_not_share_metrics(self) -> None:
        """Test do not share metrics instances."""
        font = Path("C:/Windows/Fonts/bahnschrift.ttf")
        plems = pad_text(font, ["one", "two", "three"])
        for i, p in enumerate(plems, start=1):
            p.font_size = i
        assert math.isclose(plems[0].height * 2, plems[1].height)

    def test_has_leading(self) -> None:
        """Test pad_text with a font file."""
        font = Path("C:/Windows/Fonts/bahnschrift.ttf")
        if not font.exists():
            msg = "Test font file does not exist on system."
            pytest.skip(msg)
        padded = pad_text(font, "Lorem ipsum dolor")
        assert padded.leading == padded.height + padded.metrics.line_gap

    def test_multiple_text_args(self) -> None:
        """Test pad_text a list of strings."""
        font = Path("C:/Windows/Fonts/bahnschrift.ttf")
        if not font.exists():
            msg = "Test font file does not exist on system."
            pytest.skip(msg)
        padded = pad_text(font, ["Lorem", "ipsum", "dolor"])
        assert len(padded) == 3


class TestWrapTextFt:
    def test_wraps_single(self) -> None:
       """Test pad_text with a font file."""
       font = Path("C:/Windows/Fonts/bahnschrift.ttf")
       text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed"
       expect = ["Lorem ipsum dolor sit", "amet, consectetur", "adipiscing elit, sed"]
       result = wrap_text_ft(font, text, width=20000)
       assert result == expect

    def test_wraps_multi(self) -> None:
       """Test pad_text with a font file."""
       font = Path("C:/Windows/Fonts/bahnschrift.ttf")
       text = ["Lorem ipsum dolor sit amet,", "consectetur adipiscing elit, sed"]
       expect = [
            ["Lorem ipsum", "dolor sit amet,"],
            ["consectetur", "adipiscing elit,", "sed"],
       ]
       result = wrap_text_ft(font, text, width=15000)
       assert result == expect
