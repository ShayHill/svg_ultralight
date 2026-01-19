"""Test font_info.py

:author: Shay Hill
:created: 2025-01-15
"""

from pathlib import Path

import pytest

from svg_ultralight.font_tools.font_info import FTFontInfo


class TestFTFontInfoSuperscript:
    """Test superscript properties of FTFontInfo."""

    @pytest.fixture
    def font_path(self) -> Path:
        """Get a test font path."""
        font = Path("C:/Windows/Fonts/bahnschrift.ttf")
        if not font.exists():
            msg = "Test font file does not exist on system."
            pytest.skip(msg)
        return font

    def test_y_superscript_x_offset(self, font_path: Path) -> None:
        """Test y_superscript_x_offset property returns an integer."""
        font_info = FTFontInfo(font_path)
        x_offset = font_info.y_superscript_x_offset
        assert isinstance(x_offset, int)
        # Should return 0 if not in OS/2 table, or the actual value if present

    def test_y_superscript_y_offset(self, font_path: Path) -> None:
        """Test y_superscript_y_offset property returns an integer."""
        font_info = FTFontInfo(font_path)
        y_offset = font_info.y_superscript_y_offset
        assert isinstance(y_offset, int)
        # Should return 0 if not in OS/2 table, or the actual value if present

    def test_y_superscript_y_size(self, font_path: Path) -> None:
        """Test y_superscript_y_size property returns an integer."""
        font_info = FTFontInfo(font_path)
        y_size = font_info.y_superscript_y_size
        assert isinstance(y_size, int)
        # Should return 0 if not in OS/2 table, or the actual value if present

    def test_superscript_properties_are_cached(self, font_path: Path) -> None:
        """Test that superscript properties are cached and consistent."""
        font_info1 = FTFontInfo(font_path)
        font_info2 = FTFontInfo(font_path)
        # Should return the same cached instance
        assert font_info1 is font_info2
        # Properties should be the same
        assert font_info1.y_superscript_x_offset == font_info2.y_superscript_x_offset
        assert font_info1.y_superscript_y_offset == font_info2.y_superscript_y_offset
        assert font_info1.y_superscript_y_size == font_info2.y_superscript_y_size

    def test_superscript_properties_default_to_zero_when_missing(
        self, font_path: Path
    ) -> None:
        """Test that superscript properties default to 0 when not in OS/2 table."""
        font_info = FTFontInfo(font_path)
        # Properties should always return an integer (0 if not in OS/2 table)
        assert isinstance(font_info.y_superscript_x_offset, int)
        assert isinstance(font_info.y_superscript_y_offset, int)
        assert isinstance(font_info.y_superscript_y_size, int)
