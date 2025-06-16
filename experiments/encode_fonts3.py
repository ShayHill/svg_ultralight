"""Deterministically encode a font into a base64 string for CSS.

This works fine for a browser, but there is little point. There is no way to
rasterize a css file with an embedded font like this. Learned some things doing it,
but Inkscape, Gimp, and everything else I've tried *except* a browser will ignore an
embedded or locally linked file in a `<style>` element.

:author: Shay Hill
:created: 2025-06-15
"""

# pyright: reportMissingTypeStubs = false
# pyright: reportUnknownMemberType = false
# pyright: reportUnknownVariableType = false

from __future__ import annotations

import cssutils
import base64
import os
import tempfile
from pathlib import Path

from svg_ultralight.string_conversion import (
    encode_to_css_class_name,
    decode_from_css_class_name,
)

from fontTools.subset import Subsetter
from fontTools.ttLib import TTFont
from fontTools.ttLib.woff2 import compress
import string
import warnings
from typing import Iterable, TYPE_CHECKING

if TYPE_CHECKING:
    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )


_WESTERN_UTF8_CHAR_SETS = [
    string.ascii_lowercase,
    string.ascii_uppercase,
    string.digits,
    string.punctuation,
    "áÁéÉíÍóÓúÚñÑäÄëËïÏöÖüÜçÇàÀèÈìÌòÒùÙâÂêÊîÎôÔûÛãÃõÕåÅæÆøØœŒßÿŸ",
]


def get_robust_char_subset(
    text: str, char_sets: Iterable[Iterable[str]] = _WESTERN_UTF8_CHAR_SETS
) -> str | None:
    """Infer a subset of characters likely to be used from a sample text.

    :param text: Sample text to infer the subset from.
    :param char_sets: List of character sets to use for inference. Each set is a
        string of characters. The default is a list of common western UTF-8
        character sets. Include all characters from any set that is used in the text.
    :return: A string of characters that are likely to be used in the text. Default
        subsets to include are lowercase, uppercase, digits, punctuation, and a set
        of common western diacritics. Space is always included.

    This function is for selecting which characters will be encoded inside a css
    class--which is itself inside an svg file.

    Fonts can be large. The smallest solution is to only encode the characters used
    in the text, but that can be inflexible. A robust subset allows characters that
    are similar to the text, so there is a little room to correct spelling or alter
    the text.
    """
    char_sets_ = [set(x) for x in char_sets]
    chars_known = {" "}.union(*char_sets)
    chars_used = set(text)
    if chars_used - chars_known:
        warnings.warn("Cannot create subset char sets. Returning None.")
        return None

    subset = {" "}
    for char_set in char_sets_:
        if chars_used & char_set:
            subset |= char_set
    return "".join(sorted(subset))


def font_to_woff2(
    font_path: str | os.PathLike[str],
    woff2_path: str | os.PathLike[str],
    subset: str | None = None,
) -> None:
    """Convert a (subset of a) font to woff2.

    :param font_path: Path to the original font file. Ttf and otf both work, but otf
        may show warnings (implemented as logging messages in fontTools. I have not
        silenced these. It may be a better idea to avoid subsetting otf fonts.
    :param woff2_path: Path to output.
    :param subset: String of characters to include in the subset. If None, the entire
        font is used.
    """
    font = TTFont(font_path, recalcTimestamp=False)
    font.flavor = "woff2"

    if subset is not None:
        subsetter = Subsetter()
        unicodes = set(map(ord, subset))
        subsetter.populate(unicodes=unicodes)
        subsetter.subset(font)

    font.save(woff2_path)


def encode_font_to_woff2_base64(
    font_path: str | os.PathLike[str], subset: str | None = None
) -> str:
    """Encode a WOFF2 font file to a base64 string useable in CSS.

    :param font_path: Path to the original font file. Ttf and otf both work, but otf
        may show warnings (implemented as logging messages in fontTools. I have not
        silenced these. It may be a better idea to avoid subsetting otf fonts.
    :param subset: String of characters to include in the subset. If None, the entire
        font is used.
    """
    with tempfile.NamedTemporaryFile(suffix=".woff2", delete=False) as f:
        woff2_path = f.name
    with tempfile.NamedTemporaryFile(suffix=".woff2", delete=False) as f:
        woff2_compressed = f.name

    try:
        font_to_woff2(font_path, woff2_path, subset)
        compress(woff2_path, woff2_compressed)
        with open(woff2_compressed, "rb") as woff2_file:
            woff2_data = woff2_file.read()
        return base64.b64encode(woff2_data).decode("utf-8")
    finally:
        os.unlink(woff2_path)
        os.unlink(woff2_compressed)


def _find_font_file(name: str, *font_dirs: str | os.PathLike[str]) -> Path | None:
    """Find a font file in the given directories.

    :param name: The name of the font file to find.
    :param font_dirs: Directories to search for the font file.
    :return: The path to the font file if found, otherwise None.
    """
    if not font_dirs:
        return None
    for file in Path(font_dirs[0]).glob("*"):
        if file.is_file() and file.name == name:
            return Path(file)
    return _find_font_file(name, *font_dirs[1:])


def encode_local_fonts(root: EtreeElement, *font_dirs: str | os.PathLike[str]) -> None:
    """Encode all local fonts in the given SVG root element.

    :param root: The root element of the SVG document.
    :param font_dirs: directories to search for local fonts.
    """
    font2text: dict[str, set[str]] = {}
    for elem in root.iterdescendants("text"):
        elem_class = elem.attrib.get("class", "")
        if elem_class[-7:].lower() not in {"_2e_ttf", "_2e_otf"}:
            continue
        _ = font2text.setdefault(elem_class, set())
        font2text[elem_class] |= set(elem.text or "")

    if not font2text:
        return

    encoded: list[tuple[str, str]] = []
    for font_class, chars in font2text.items():
        font_name = decode_from_css_class_name(font_class)
        font_file = _find_font_file(font_name, *font_dirs)
        if font_file is None:
            msg = f"Font file '{font_name}' not found in specified directories."
            raise FileNotFoundError(msg)

        base64 = encode_font_to_woff2_base64(font_file, subset="".join(chars))
        encoded.append((font_class, base64))

    style = root.find("style")
    if style is None:
        style = new_element("style", type="text/css")
        root.insert(0, style)
    css = style.text or ""
    stylesheet = cssutils.parseString(css)

    for font_class, base64 in encoded:
        font_face_rule = cssutils.css.CSSFontFaceRule()
        font_face_rule.style = cssutils.css.CSSStyleDeclaration()
        font_face_rule.style["font-family"] = f'{font_class}'
        font_face_rule.style["src"] = f"url('data:font/woff2;base64,{base64}') format('woff2')"
        stylesheet.add(font_face_rule)

        style_rule = cssutils.css.CSSStyleRule(selectorText=f".{font_class}")
        style_rule.style = cssutils.css.CSSStyleDeclaration()
        style_rule.style["font-family"] = f'"{font_class}"'
        stylesheet.add(style_rule)

    style.text = stylesheet.cssText.decode("utf-8")


from svg_ultralight.main import new_svg_root
from svg_ultralight.constructors import new_element, new_sub_element

root = new_svg_root(x_=0, y_=-10, width_=100, height_=100)

class_ = encode_to_css_class_name("AGENCYB.TTF")
for i in range(6):
    _ = new_sub_element(root, "text", text=f"Hello World {i}", class_=class_)


FONTS_DIRS = [
    Path(r"C:\Windows\Fonts"),
    Path(r"C:\Users\shaya\AppData\Local\Microsoft\Windows\Fonts"),
]

encode_local_fonts(root, *FONTS_DIRS)

from svg_ultralight.main import write_svg

# _ = write_svg("temp.svg", root)

import time

# Example usage:
from pathlib import Path
import random

# input_font = str(Path("C:/Windows/Fonts/AGENCYB.TTF"))
# aaa = None
# bbb = None
# for i in range(10):
#     if i % 3 == 0:
#         chars = "".join(list(set(input_font)))
#     elif i % 3 == 1:
#         chars = get_robust_char_subset(input_font)
#     else:
#         chars = None
#     print(chars)
#     result = encode_woff2_to_base64(input_font, chars)
#     bbb = result
#     aaa = aaa or bbb
#     print(aaa == bbb)
#     print(len(bbb))
#     aaa = bbb
#     time.sleep(1)  # Sleep for 1 second to avoid rapid file creation
