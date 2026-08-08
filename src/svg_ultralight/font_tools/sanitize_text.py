"""Convert unicode text to a safe ASCII representation.

FTTextInfo produces an EtreeElement. This element is an atomized string, where each
character is a path object with a `font-info` attribute that is the font character
from which the path was derived.

<group>
  <path font-info="H" d="..."/>
  <path font-info="e" d="..."/>
  <path font-info="l" d="..."/>
  <path font-info="l" d="..."/>
  <path font-info="o" d="..."/>
</group>

This facilitates debugging and some animation effects. While the EtreeElement is in
memory, the font-info value can be any character, but many characters cannot or
should not be written to file, even some ascii characters.

This module provides a converter for making unicode and unsafe ascii characters safe
for writing to file as attribute values. The transformation cannot be reversed. These
values are only written an human-readable hints for debugging or examining output svg
files.

Will raise a ValueError for any whitespace or control characters in the input string.
This is partly a sanity test. Whitespace and control characters do not have glyphs,
so should never be part of a data-text attribute.

This provides four guarantees:
1. Hints are n-character long given n-character input.
2. No problematic characters (&, <, >, ") or characters which must be escaped
   (no slashes or even double quotes)
3. No line breaks or other control characters (raises ValueError).
4. No whitespace characters (raises ValueError).

:author: Shay Hill
:created: 2026-08-07
"""

import unicodedata

_QUOTES = '"\u201c\u201d\u2018\u2019\u201e\u201a\u00ab\u00bb'
_DASHES = "\u2014\u2013"
_SLASHES = "\\/"
_PROBLEMATIC = "&<>"
_TEXT_TRANS = str.maketrans(
    {
        **dict.fromkeys(_QUOTES, "'"),
        **dict.fromkeys(_DASHES, "-"),
        **dict.fromkeys(_SLASHES, "|"),
        **dict.fromkeys(_PROBLEMATIC, "?"),
    }
)


def sanitize_data_text_value(text: str) -> str:
    """Convert a string to a safe ASCII representation for an svg property.

    :param text: Only ever call with the value of a character path element `svg-text`
        attribute value or a concatenation of such values.

    1. Result is n-characters long given n-character input.
    2. No problematic characters (&, <, >, ") or characters which must be escaped
       (no slashes or even double quotes)
    3. No line breaks or other control characters (raises ValueError).
    4. No whitespace characters (raises ValueError).
    """
    result: list[str] = []
    if any(unicodedata.category(c) == "Cc" for c in text):
        msg = f"Input string contains control characters: {text!r}"
        raise ValueError(msg)
    if any(char.isspace() for char in text):
        msg = f"Input string contains whitespace characters: {text!r}"
        raise ValueError(msg)
    for char in text.translate(_TEXT_TRANS):
        if ord(char) < 128:
            result.append(char)
            continue
        decomposed = (
            unicodedata.normalize("NFKD", char)
            .encode("ascii", "ignore")
            .decode("ascii")
        )
        result.append(decomposed if len(decomposed) == 1 else "?")
    return "".join(result)

