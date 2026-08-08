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
  by the one-path-per-character format. Default False.

- reuse paths by moving duplicate path data strings into a defs section and replacing
  the elements with use elements. Will do this for any path in the file (text or no)
  used more than once. This will allow long text strings in a relatively small svg
  file. The defs section will form an alphabet of glyphs, and each glyph will only
  need a short `use` element. Default False. Default True when called from write_svg.

:author: Shay Hill
:created: 2025-06-07
"""

from __future__ import annotations

import unicodedata
import uuid
from typing import TYPE_CHECKING

from svg_path_data import get_cpts_from_svgd, get_svgd_from_cpts

from svg_ultralight.constructors import new_element, update_element
from svg_ultralight.transformations import get_transform_matrix, mat_apply

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

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


# ===================================================================================
#   Generate unique IDs for path elements in defs
# ===================================================================================


_ALPHANUM = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


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
#   Join consecutive character paths into a single path.
# ===================================================================================


def _is_next_consecutive(path_a: EtreeElement, path_b: EtreeElement) -> bool:
    """Check if two path elements are consecutive siblings in the tree.

    :param path_a: the first path element
    :param path_b: the second path element
    :return: True if the two paths are consecutive siblings, False otherwise
    """
    parent_a = path_a.getparent()
    parent_b = path_b.getparent()
    if parent_a is None or parent_b is None or parent_a != parent_b:
        return False
    index_a = parent_a.index(path_a)
    index_b = parent_b.index(path_b)
    return index_b - index_a == 1


def _in_next_and_joinable(path_a: EtreeElement, path_b: EtreeElement) -> bool:
    """Check if two path elements are joinable and consecutive.

    :param path_a: the first path element
    :param path_b: the second path element
    :return: True if the two paths are joinable and consecutive, False otherwise
    """
    if not _is_next_consecutive(path_a, path_b):
        return False
    attrib_a = {**path_a.attrib}
    attrib_b = {**path_b.attrib}
    if attrib_a.get("data-text") is None or attrib_b.get("data-text") is None:
        return False
    skip = {"id", "data-text", "transform", "d"}
    for key in (x for x in set(attrib_a) | set(attrib_b) if x not in skip):
        if attrib_a.get(key) != attrib_b.get(key):
            return False
    return True


_IDENTITY = (1, 0, 0, 1, 0, 0)  # identity matrix for SVG transforms


def _transform_svgd(elem: EtreeElement) -> None:
    """Apply the transform attribute to the path data and remove the transform."""
    transform = get_transform_matrix(elem)
    if transform == _IDENTITY:
        _ = elem.attrib.pop("transform", None)
        return
    cpts = get_cpts_from_svgd(elem.attrib.get("d", ""))
    if not cpts:
        return
    cpts = [[mat_apply(transform, x) for x in path] for path in cpts]
    _ = update_element(elem, d=get_svgd_from_cpts(cpts))
    _ = elem.attrib.pop("transform", None)


def _join_char_paths(root: EtreeElement) -> None:
    """Join consecutive path elements that have the same attributes."""
    # transform all path elements if they are text
    defs = next((x for x in root if x.tag == "defs"), None)
    paths = [x for x in _iter_paths(root, defs) if x.attrib.get("data-text")]
    for path in paths:
        _transform_svgd(path)
    i = 1
    while i < len(paths) and i > 0:
        path_a = paths[i - 1]
        path_b = paths[i]
        if _in_next_and_joinable(path_a, path_b):
            svgd = path_a.attrib.get("d", "") + path_b.attrib.get("d", "")
            data_text = path_a.attrib.get("data-text", "") + path_b.attrib.get(
                "data-text", ""
            )
            _ = update_element(path_a, data_text=data_text, d=svgd)
            parent = path_b.getparent()
            if parent is None:
                msg = "Path element has no parent, cannot remove."
                raise RuntimeError(msg)
            parent.remove(path_b)
            _ = paths.pop(i)
        else:
            i += 1


# ===================================================================================
#   Reuse paths by moving duplicate path data strings into a defs section and
#   replacing with use elements.
# ===================================================================================


def _iter_paths(
    root: EtreeElement, defs: EtreeElement | None
) -> Iterator[EtreeElement]:
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
    children = (
        [x for x in root if x.tag != "path"]
        if defs is not None and root is defs
        else root
    )
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


def _new_id_getter(seen: set[str] | None = None) -> Callable[[str], str]:
    """Return a function that takes a base_id and returns a unique ID.

    :param seen: set of IDs that are already in use (updated as IDs are yielded).
        This is optional, for if you'd prefer some unique id sequences start with
        "{base_id}_0" instead of "{base_id}".
    """
    seen = seen or set()
    base_id2id_gen: dict[str, Iterator[str]] = {}

    def get_next_unique_id(base_id: str) -> str:
        """Select a generator for the base_id and return the next unique ID."""
        gen = base_id2id_gen.setdefault(base_id, _unique_id_generator(base_id, seen))
        return next(gen)

    return get_next_unique_id


# A placeholder value to indicate that a value has only been seen once. For
# _map_paths_to_ids, where IDs are only generated for values that have been seen at
# least twice.
_SEEN_ONCE = str(uuid.uuid4())


def _map_paths_to_ids(root: EtreeElement) -> dict[str, str]:
    """Map any data strings used multiple times to unique IDs."""
    defs = next((x for x in root if x.tag == "defs"), None)
    svgd2id: dict[str, str] = {}
    get_next_unique_id = _new_id_getter()
    for path in _iter_paths(root, defs):
        svgd = path.attrib.get("d")
        if svgd is None or not svgd:
            continue
        current_id = svgd2id.get(svgd)
        if current_id not in (_SEEN_ONCE, None):  # already assigned
            continue
        if path.attrib.get("data-text") is not None or current_id == _SEEN_ONCE:
            svgd2id[svgd] = get_next_unique_id(path.attrib.get("data-text", "path"))
            continue
        svgd2id[svgd] = _SEEN_ONCE
    return {k: v for k, v in svgd2id.items() if v != _SEEN_ONCE}


def _reuse_paths(root: EtreeElement) -> None:
    """Define paths in the defs section of the SVG.

    :param root: the root element of an svg
    """
    svgd2id = _map_paths_to_ids(root)
    if not svgd2id:
        return
    defs = _find_or_create_defs(root)
    for svgd, id_ in reversed(svgd2id.items()):
        path = new_element("path", id_=id_, d=svgd)
        defs.insert(0, path)
    for path in _iter_paths(root, defs):
        svgd = path.attrib.get("d", "")
        id_ = svgd2id.get(svgd, "")
        if not id_:
            continue
        parent = path.getparent()
        if parent is None:
            msg = "Path element has no parent, cannot replace."
            raise RuntimeError(msg)
        pass_attrib = {
            k: v for k, v in path.attrib.items() if k not in {"d", "data-text"}
        }
        replacement = new_element("use", href=f"#{id_}", **pass_attrib)
        ix = parent.index(path)
        parent.insert(ix, replacement)
        parent.remove(path)


def sanitize_text(
    root: EtreeElement, *, deatomize: bool = False, reuse_paths: bool = False
) -> None:
    """Sanitize text paths in an SVG.

    :param root: the root element of an svg
    :param deatomize: if True, merge consecutive character paths into a single path
    :param reuse_paths: if True, move duplicate path data strings into a defs section
        and replace the elements with use elements
    """
    defs = next((x for x in root if x.tag == "defs"), None)
    for path in _iter_paths(root, defs):
        if "data-text" in path.attrib:
            path.attrib["data-text"] = sanitize_data_text_value(
                path.attrib["data-text"]
            )
    if deatomize:
        _join_char_paths(root)
    if reuse_paths:
        _reuse_paths(root)
