"""Test functions in sanitize_text.py.

Three guarantees under test:
1. Output length equals input length (n chars in, n chars out).
2. No problematic characters in output: & < > " \\ /
3. No control characters in output (no non-printables).

Whitespace in input must raise ValueError.

:author: Shay Hill
:created: 2026-08-07
"""

import unicodedata
from contextlib import suppress

import pytest

from svg_ultralight.font_tools.sanitize_text import sanitize_data_text_value

_PROBLEMATIC = {"&", "<", ">", '"', "\\", "/"}

# Computed at import time to track Python's actual isspace() definition.
_WS_ASCII = [c for c in range(128) if chr(c).isspace()]
_NONWS_ASCII = [c for c in range(128) if not chr(c).isspace()]


class TestWhitespaceRaises:
    """Whitespace anywhere in input must raise ValueError."""

    @pytest.mark.parametrize("code", _WS_ASCII)
    def test_ascii_whitespace_raises(self, code: int) -> None:
        if unicodedata.category(chr(code)) == "Cc":
            return
        with pytest.raises(ValueError, match="whitespace"):
            _ = sanitize_data_text_value(chr(code))

    @pytest.mark.parametrize(
        "char", ["\u00a0", "\u2003", "\u2028", "\u2029", "\u3000", "\u0085"]
    )
    def test_unicode_whitespace_raises(self, char: str) -> None:
        if unicodedata.category(char) == "Cc":
            match = "control"
        else:
            match = "whitespace"
        with pytest.raises(ValueError, match=match):
            _ = sanitize_data_text_value(char)

    def test_whitespace_in_middle_raises(self) -> None:
        with pytest.raises(ValueError, match="whitespace"):
            _ = sanitize_data_text_value("no tab")

    def test_leading_whitespace_raises(self) -> None:
        with pytest.raises(ValueError, match="whitespace"):
            _ = sanitize_data_text_value(" leading")

    def test_trailing_whitespace_raises(self) -> None:
        with pytest.raises(ValueError, match="whitespace"):
            _ = sanitize_data_text_value("trailing ")


class TestLengthPreserved:
    """Output length equals input length for every non-whitespace input."""

    @pytest.mark.parametrize("code", _NONWS_ASCII)
    def test_ascii_length(self, code: int) -> None:
        if unicodedata.category(chr(code)) == "Cc":
            return
        assert len(sanitize_data_text_value(chr(code))) == 1

    def test_unicode_length(self) -> None:
        some_unicode = "éàüÀﬁﬂΩ℃\U0001f600\U0001f1fa\u2014\u2013—“”«»­中Ω﹤﹥"
        assert len(sanitize_data_text_value(some_unicode)) == len(some_unicode)


class TestNoProblematic:
    """No problematic characters appear in the output."""

    @pytest.mark.parametrize("code", _NONWS_ASCII)
    def test_ascii_no_problematic(self, code: int) -> None:
        with suppress(ValueError):
            result = sanitize_data_text_value(chr(code))
            assert result not in _PROBLEMATIC, f"chr({code}) → {result!r}"

    def test_string_no_problematic(self) -> None:
        result = sanitize_data_text_value("&<>" + '"' + "\\/")
        assert not any(c in _PROBLEMATIC for c in result), repr(result)


# ── Guarantee 3: no control characters in output ─────────────────────────────


class TestNoControl:
    """No control characters appear in the output."""

    @pytest.mark.parametrize("code", _NONWS_ASCII)
    def test_ascii_no_control(self, code: int) -> None:
        if unicodedata.category(chr(code)) != "Cc":
            return
        with pytest.raises(ValueError, match="control"):
            _ = sanitize_data_text_value(chr(code))

    @pytest.mark.parametrize(
        "text",
        [
            "null\x00char",
            "bell\x07beep",
            "esc\x1bseq",
            "del\x7fchar",
            "\x01\x02\x03\x04\x05\x06",
            "\x0e\x0f\x10\x1e\x1f",
        ],
    )
    def test_string_no_control(self, text: str) -> None:
        with pytest.raises(ValueError, match="control"):
            _ = sanitize_data_text_value(text)
