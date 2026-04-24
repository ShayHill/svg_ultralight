"""Move duplicate path data strings into ``defs`` and reference via ``use``.

:author: Shay Hill
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from svg_ultralight.constructors import new_element

if TYPE_CHECKING:
    from collections.abc import Iterator

    from lxml.etree import _Element as EtreeElement

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


def reuse_paths(root: EtreeElement) -> None:
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
