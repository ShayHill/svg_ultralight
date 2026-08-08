"""Sanitize text elements produced by FTTextInfo.

Run this before writing an svg file to disk.

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

## Optional effects:

- deatomize text by merging consecutive character paths. This will take a bit of
  processing load off whatever is reading the svg and will sometimes make the file
  smaller. Mostly, it's a preference if you do not like the vertical space taken up
  by the one-path-per-character format. Off by default.

- reuse paths by moving duplicate path data strings into a defs section and replacing
  the elements with use elements. Will do this for all single-character paths (have a
  1-character `data-text` attribute) and for any other path in the file (text or no)
  used more than once. This will allow long text strings in a relatively small svg
  file. The defs section will form an alphabet of glyphs, and each glyph will only
  need a short use element. On by default.

:author: Shay Hill
:created: 2025-06-07
"""

from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING

from svg_ultralight.constructors import new_element

if TYPE_CHECKING:
    from collections.abc import Iterator

    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )


# ===================================================================================
#   Sanitize the data-text values
# ===================================================================================


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


_ALPHANUM = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ===================================================================================
#   Generate unique IDs for path elements in defs
# ===================================================================================


def _unique_id_generator(id_: str, seen: set[str]) -> Iterator[str]:
    """Generate unique IDs for a given base ID.

    :param id_: the base ID to generate unique variants for
    :param seen: set of IDs that are already in use (updated as IDs are yielded)
    :yield: unique ID candidates
    """
    if id_ not in seen:
        seen.add(id_)
        yield id_
    for length in range(1, 5):
        for suffix in _generate_alphanumeric(length):
            candidate = f"{id_}{suffix}"
            if candidate in seen:
                continue
            seen.add(candidate)
            yield candidate


def _generate_alphanumeric(length: int) -> Iterator[str]:
    """Generate alphanumeric strings of a given length.

    :param length: the length of strings to generate
    :yield: alphanumeric strings
    """
    if length == 1:
        for char in _ALPHANUM:
            yield char
    else:
        for prefix in _generate_alphanumeric(length - 1):
            for char in _ALPHANUM:
                yield prefix + char


# ===================================================================================
#   Reuse paths by moving duplicate path data strings into a defs section and
#   replacing with use elements.
# ===================================================================================


def _iter_paths(root: EtreeElement, defs: EtreeElement) -> Iterator[EtreeElement]:
    """Iterate over the path elements that are not the top defs section.

    :param root: the root element of an svg
    :param defs: the top-level defs section
    :param exclude: the element to exclude from the iteration (the top defs section)
    :yield: the path elements that are not in the top defs section
    """
    if root.tag == "path" and "d" in root.attrib:
        yield root
        return
    # if within defs, don't strip data strings from path elements, but do descend into
    # `g` elements which may contain paths.
    children = [x for x in root if x.tag != "path"] if root is defs else root
    for child in children:
        yield from _iter_paths(child, defs)


def _find_or_create_defs(root: EtreeElement) -> EtreeElement:
    """Find a defs section at the top of the SVG or create it if it doesn't exist.

    :param root: the root element of an svg
    :return: the defs section of the SVG
    """
    try:
        return next(x for x in root if x.tag == "defs")
    except StopIteration:
        defs = new_element("defs")
        root.insert(0, defs)
        return defs


def _reuse_paths(root: EtreeElement) -> None:
    """Define paths in the defs section of the SVG.

    :param root: the root element of an svg
    """
    d2id: dict[str, str] = {}
    base_id2ids: dict[str, Iterator[str]] = {}
    seen: set[str] = set()
    defs = _find_or_create_defs(root)
    for path in _iter_paths(root, defs):
        svgd = path.attrib["d"]
        if svgd == "":
            continue
        if svgd in d2id:
            id_ = d2id[svgd]
        else:
            base_id = path.attrib.get("data-text", "path")
            if base_id not in base_id2ids:
                if isinstance(path.tag, str) and path.tag.endswith(base_id):
                    seen.add(base_id)
                base_id2ids[base_id] = _unique_id_generator(base_id, seen)
            id_ = next(base_id2ids[base_id])
            d2id[svgd] = id_
        parent = path.getparent()
        if parent is None:
            msg = "Path element has no parent, cannot replace."
            raise RuntimeError(msg)
        pass_attrib = {k: v for k, v in path.attrib.items() if k != "d"}
        replacement = new_element("use", href=f"#{d2id[svgd]}", **pass_attrib)
        ix = parent.index(path)
        parent.insert(ix, replacement)
        parent.remove(path)
    for svgd, id_ in reversed(d2id.items()):
        path = new_element("path", id_=id_, d=svgd)
        defs.insert(0, path)
    if len(defs) == 0:
        root.remove(defs)


def sanitize_text(
    root: EtreeElement, *, deatomize: bool = False, reuse_paths: bool = True
) -> None:
    """Sanitize text paths in an SVG.

    :param root: the root element of an svg
    :param deatomize: if True, merge consecutive character paths into a single path
    :param reuse_paths: if True, move duplicate path data strings into a defs section
        and replace the elements with use elements
    """
    del deatomize

    for path in _iter_paths(root, _find_or_create_defs(root)):
        if "data-text" in path.attrib:
            path.attrib["data-text"] = sanitize_data_text_value(
                path.attrib["data-text"]
            )

    if reuse_paths:
        _reuse_paths(root)
