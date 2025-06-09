"""Test padded_text_initializers.py

:author: Shay Hill
:created: 2025-06-09
"""
from pathlib import Path

import pytest

from svg_ultralight.bounding_boxes.padded_text_initializers import pad_text, pad_text_ft
from svg_ultralight.constructors import new_element

INKSCAPE = Path(r"C:\Program Files\Inkscape\bin\inkscape")

class TestPadText:
    def test_font_arg(self) -> None:
        """Test to see that the font specification does *something*."""
        font = Path("C:/Windows/Fonts/bahnschrift.ttf")
        if not font.exists():
            msg = "Test font file does not exist on system."
            pytest.skip(msg)
        if not INKSCAPE.exists():
            msg = "Inkscape executable does not exist on system."
            pytest.skip(msg)
        test_elem = new_element("text", text="Lorem ipsum dolor", font_size=12)
        no_font = pad_text(INKSCAPE, test_elem)
        with_font = pad_text(INKSCAPE, test_elem, font=font)
        assert no_font.bbox.height != with_font.bbox.height

    def test_pad_text_line_gap(self) -> None:
        """A PaddedText instance created by pad_text has no line gap by default."""
        if not INKSCAPE.exists():
            msg = "Inkscape executable does not exist on system."
            pytest.skip(msg)
        test_elem = new_element("text", text="Lorem ipsum dolor", font_size=12)
        padded = pad_text(INKSCAPE, test_elem)
        with pytest.raises(AttributeError):
            _ = padded.line_gap

    def test_pad_text_set_line_gap(self) -> None:
        """A PaddedText instance created by pad_text has a line_gap if set."""
        if not INKSCAPE.exists():
            msg = "Inkscape executable does not exist on system."
            pytest.skip(msg)
        test_elem = new_element("text", text="Lorem ipsum dolor", font_size=12)
        padded = pad_text(INKSCAPE, test_elem)
        padded.line_gap = 5
        assert padded.line_gap == 5

    def test_pad_text_no_leading(self) -> None:
        """A PaddedText instance created by pad_text has no leading by default."""
        if not INKSCAPE.exists():
            msg = "Inkscape executable does not exist on system."
            pytest.skip(msg)
        test_elem = new_element("text", text="Lorem ipsum dolor", font_size=12)
        padded = pad_text(INKSCAPE, test_elem)
        with pytest.raises(AttributeError):
            _ = padded.leading

    def test_pad_text_set_leading_by_setting_line_gap(self) -> None:
        if not INKSCAPE.exists():
            msg = "Inkscape executable does not exist on system."
            pytest.skip(msg)
        test_elem = new_element("text", text="Lorem ipsum dolor", font_size=12)
        padded = pad_text(INKSCAPE, test_elem)
        padded.line_gap = 5
        assert padded.leading == padded.height + 5

class TestPadTextFt:
    pass
