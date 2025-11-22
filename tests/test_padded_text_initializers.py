"""Test padded_text_initializers.py

:author: Shay Hill
:created: 2025-06-09
"""

from pathlib import Path

import pytest
from conftest import INKSCAPE, has_inkscape

from svg_ultralight.bounding_boxes.padded_text_initializers import (
    pad_text,
    pad_text_ft,
    pad_chars_ft,
    wrap_text_ft,
)
from svg_ultralight.bounding_boxes.type_bound_element import BoundElement

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
        no_font = pad_text(INKSCAPE, test_elem)
        with_font = pad_text(INKSCAPE, test_elem, font=font)
        assert no_font.bbox.height != with_font.bbox.height

    @pytest.mark.skipif(not has_inkscape(INKSCAPE), reason="Inkscape not found")
    def test_pad_text_line_gap(self) -> None:
        """A PaddedText instance created by pad_text has no line gap by default."""
        test_elem = new_element("text", text="Lorem ipsum dolor", font_size=12)
        padded = pad_text(INKSCAPE, test_elem)
        with pytest.raises(AttributeError):
            _ = padded.line_gap

    @pytest.mark.skipif(not has_inkscape(INKSCAPE), reason="Inkscape not found")
    def test_pad_text_set_line_gap(self) -> None:
        """A PaddedText instance created by pad_text has a line_gap if set."""
        test_elem = new_element("text", text="Lorem ipsum dolor", font_size=12)
        padded = pad_text(INKSCAPE, test_elem)
        padded.line_gap = 5
        assert padded.line_gap == 5

    @pytest.mark.skipif(not has_inkscape(INKSCAPE), reason="Inkscape not found")
    def test_pad_text_no_leading(self) -> None:
        """A PaddedText instance created by pad_text has no leading by default."""
        test_elem = new_element("text", text="Lorem ipsum dolor", font_size=12)
        padded = pad_text(INKSCAPE, test_elem)
        with pytest.raises(AttributeError):
            _ = padded.leading

    @pytest.mark.skipif(not has_inkscape(INKSCAPE), reason="Inkscape not found")
    def test_pad_text_set_leading_by_setting_line_gap(self) -> None:
        test_elem = new_element("text", text="Lorem ipsum dolor", font_size=12)
        padded = pad_text(INKSCAPE, test_elem)
        padded.line_gap = 5
        assert padded.leading == padded.height + 5


class TestPadTextFt:
    def test_has_line_gap(self) -> None:
        """Test pad_text_ft with a font file."""
        font = Path("C:/Windows/Fonts/bahnschrift.ttf")
        if not font.exists():
            msg = "Test font file does not exist on system."
            pytest.skip(msg)
        padded = pad_text_ft(font, "Lorem ipsum dolor")
        assert padded.line_gap > 0

    def test_has_leading(self) -> None:
        """Test pad_text_ft with a font file."""
        font = Path("C:/Windows/Fonts/bahnschrift.ttf")
        if not font.exists():
            msg = "Test font file does not exist on system."
            pytest.skip(msg)
        padded = pad_text_ft(font, "Lorem ipsum dolor")
        assert padded.leading == padded.height + padded.line_gap

    def test_multiple_text_args(self) -> None:
        """Test pad_text_ft a list of strings."""
        font = Path("C:/Windows/Fonts/bahnschrift.ttf")
        if not font.exists():
            msg = "Test font file does not exist on system."
            pytest.skip(msg)
        padded = pad_text_ft(font, ["Lorem", "ipsum", "dolor"])
        assert len(padded) == 3


class TestWrapTextFt:
    def test_wraps_single(self) -> None:
        """Test pad_text_ft with a font file."""
        font = Path("C:/Windows/Fonts/bahnschrift.ttf")
        text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed"
        expect = ["Lorem ipsum dolor sit", "amet, consectetur", "adipiscing elit, sed"]
        result = wrap_text_ft(font, text, width=20000)
        assert result == expect

    def test_wraps_multi(self) -> None:
        """Test pad_text_ft with a font file."""
        font = Path("C:/Windows/Fonts/bahnschrift.ttf")
        text = ["Lorem ipsum dolor sit amet,", "consectetur adipiscing elit, sed"]
        expect = [
            ["Lorem ipsum", "dolor sit amet,"],
            ["consectetur", "adipiscing elit,", "sed"],
        ]
        result = wrap_text_ft(font, text, width=15000)
        assert result == expect


class TestPadCharsFt:

    def test_multiple_text_args(self) -> None:
        """Test pad_chars_ft a list of strings."""
        font = Path("C:/Windows/Fonts/bahnschrift.ttf")
        if not font.exists():
            msg = "Test font file does not exist on system."
            pytest.skip(msg)
        padded = pad_chars_ft(font, ["Lorem", "ipsum", "dolor"])
        assert len(padded) == 3

    def test_single_text_arg(self) -> None:
        """Test pad_chars_ft a single string."""
        font = Path("C:/Windows/Fonts/bahnschrift.ttf")
        if not font.exists():
            msg = "Test font file does not exist on system."
            pytest.skip(msg)
        padded = pad_chars_ft(font, "Lorem")
        assert isinstance(padded, BoundElement)
