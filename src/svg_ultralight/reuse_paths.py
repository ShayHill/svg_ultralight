"""Move duplicate path data strings into ``defs`` and reference via ``use``.

:author: Shay Hill
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from svg_ultralight.constructors import new_element

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )

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
            candidate = f"{id_}_{suffix}"
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
    children = [x for x in root if x.tag != "path"] if defs and root is defs else root
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
        if current_id is None:
            svgd2id[svgd] = _SEEN_ONCE
        elif current_id == _SEEN_ONCE:
            svgd2id[svgd] = get_next_unique_id(path.attrib.get("data-text", "path"))
    return {k: v for k, v in svgd2id.items() if v != _SEEN_ONCE}


def reuse_paths(root: EtreeElement) -> None:
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
        pass_attrib = {k: v for k, v in path.attrib.items() if k != "d"}
        replacement = new_element("use", href=f"#{id_}", **pass_attrib)
        ix = parent.index(path)
        parent.insert(ix, replacement)
        parent.remove(path)
