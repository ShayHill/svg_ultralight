"""Query an SVG file for bounding boxes.

:author: Shay Hill
:created: 7/25/2020

Bounding boxes are generated with a command-line call to Inkscape, so an Inkscape
installation is required for this to work. The bounding boxes are returned as
BoundingBox instances, which are a big help with aligning objects (e.g., text on a
business card). Getting bounding boxes from Inkscape is not exceptionally fast.
"""

from __future__ import annotations

import hashlib
import os
import pickle
import re
import uuid
from contextlib import suppress
from copy import deepcopy
from pathlib import Path
from subprocess import PIPE, Popen
from tempfile import NamedTemporaryFile, TemporaryFile
from typing import TYPE_CHECKING
from warnings import warn

from lxml import etree

from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.main import new_svg_root, write_svg

if TYPE_CHECKING:
    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )


with TemporaryFile() as f:
    _CACHE_DIR = Path(f.name).parent / "svg_ultralight_cache"

_CACHE_DIR.mkdir(exist_ok=True)


def _fill_ids(*elem_args: EtreeElement) -> None:
    """Set the id attribute of an element and all its children. Keep existing ids.

    :param elem: an etree element, accepts multiple arguments
    """
    if not elem_args:
        return
    elem = elem_args[0]
    for child in elem:
        _fill_ids(child)
    if elem.get("id") is None:
        elem.set("id", f"svg_ul-{uuid.uuid4()}")
    _fill_ids(*elem_args[1:])


def _normalize_views(elem: EtreeElement) -> None:
    """Create a square viewbox for any element with an svg tag.

    :param elem: an etree element

    This prevents the bounding boxes from being distorted. Only do this to copies,
    because there's no way to undo it.
    """
    for child in elem:
        _normalize_views(child)
    if str(elem.tag).endswith("svg"):
        elem.set("viewBox", "0 0 1 1")
        elem.set("width", "1")
        elem.set("height", "1")


def _envelop_copies(*elem_args: EtreeElement) -> EtreeElement:
    """Create an svg root element enveloping all elem_args.

    :param elem_args: one or more etree elements
    :return: an etree element enveloping copies of elem_args with all views normalized
    """
    envelope = new_svg_root(0, 0, 1, 1)
    envelope.extend([deepcopy(e) for e in elem_args])
    _normalize_views(envelope)
    return envelope


def map_ids_to_bounding_boxes(
    inkscape: str | Path, *elem_args: EtreeElement
) -> dict[str, BoundingBox]:
    r"""Query an svg file for bounding-box dimensions.

    :param inkscape: path to an inkscape executable on your local file system
        IMPORTANT: path cannot end with ``.exe``.
        Use something like ``"C:\\Program Files\\Inkscape\\inkscape"``
    :param elem_args: xml element (written to a temporary file then queried)
    :return: svg element ids (and a bounding box for the entire svg file as ``svg``)
        mapped to (x, y, width, height)
    :effects: adds an id attribute to any element without one. These will all have
        the prefix svg_ul-, so you can find and remove them later if desired.

    Bounding boxes are relative to svg viewbox. If viewbox x == -10,
    all bounding-box x values will be offset -10. So, everything is wrapped in a root
    element with a "normalized" viewbox, (viewbox=(0, 0, 1, 1)) then any child root
    elements ("child root elements" sounds wrong, but it works) viewboxes are
    normalized as well. This works even with a root element around a root element, so
    input elem_args can be root elements or "normal" elements like "rect", "circle",
    or "text" or a mixture of both.

    The ``inkscape --query-all svg`` call will return a tuple:

    (b'svg1,x,y,width,height\\r\\elem1,x,y,width,height\\r\\n', None)
    where x, y, width, and height are strings of numbers.

    This calls the command and formats the output into a dictionary.

    Scaling arguments ("width", "height") to new_svg_root transform the bounding
    boxes in non-useful ways.  This copies all elements except the root element in to
    a (0, 0, 1, 1) root. This will put the boxes where you'd expect them to be, no
    matter what root you use.
    """
    if not elem_args:
        return {}
    _fill_ids(*elem_args)
    envelope = _envelop_copies(*elem_args)

    with NamedTemporaryFile(mode="wb", delete=False, suffix=".svg") as svg_file:
        svg = write_svg(svg_file, envelope)
    with Popen(f'"{inkscape}" --query-all {svg}', stdout=PIPE) as bb_process:
        bb_data = str(bb_process.communicate()[0])[2:-1]
        bb_strings = re.split(r"[\\r]*\\n", bb_data)[:-1]
    os.unlink(svg_file.name)

    id2bbox: dict[str, BoundingBox] = {}
    for id_, *bounds in (x.split(",") for x in bb_strings):
        x, y, width, height = (float(x) for x in bounds)
        id2bbox[id_] = BoundingBox(x, y, width, height)
    return id2bbox


def _hash_elem(elem: EtreeElement) -> str:
    """Hash an EtreeElement.

    Will match identical (excepting id) elements.
    """
    elem_copy = deepcopy(elem)
    with suppress(KeyError):
        _ = elem_copy.attrib.pop("id")
    hash_object = hashlib.sha256(etree.tostring(elem_copy))
    return hash_object.hexdigest()


def _try_bbox_cache(elem_hash: str) -> BoundingBox | None:
    """Try to load a cached bounding box."""
    cache_path = _CACHE_DIR / elem_hash
    if not cache_path.exists():
        return None
    try:
        with cache_path.open("rb") as f:
            return pickle.load(f)
    except (EOFError, pickle.UnpicklingError) as e:
        msg = f"Error loading cache file {cache_path}: {e}"
        warn(msg)
    except Exception as e:
        msg = f"Unexpected error loading cache file {cache_path}: {e}"
        warn(msg)
    return None


def get_bounding_boxes(
    inkscape: str | Path, *elem_args: EtreeElement
) -> tuple[BoundingBox, ...]:
    r"""Get bounding box around a single element (or multiple elements).

    :param inkscape: path to an inkscape executable on your local file system
        IMPORTANT: path cannot end with ``.exe``.
        Use something like ``"C:\\Program Files\\Inkscape\\inkscape"``
    :param elem_args: xml elements
    :return: a BoundingBox instance around a each elem_arg

    This will work most of the time, but if you're missing an nsmap, you'll need to
    create an entire xml file with a custom nsmap (using
    `svg_ultralight.new_svg_root`) then call `map_ids_to_bounding_boxes` directly.
    """
    elem2hash = {elem: _hash_elem(elem) for elem in elem_args}
    cached = [_try_bbox_cache(h) for h in elem2hash.values()]
    if None not in cached:
        return tuple(filter(None, cached))

    hash2bbox = {h: c for h, c in zip(elem2hash.values(), cached) if c is not None}
    remainder = [e for e, c in zip(elem_args, cached) if c is None]
    id2bbox = map_ids_to_bounding_boxes(inkscape, *remainder)
    for elem in remainder:
        hash_ = elem2hash[elem]
        hash2bbox[hash_] = id2bbox[elem.attrib["id"]]
        with (_CACHE_DIR / hash_).open("wb") as f:
            pickle.dump(hash2bbox[hash_], f)
    return tuple(hash2bbox[h] for h in elem2hash.values())


def get_bounding_box(inkscape: str | Path, elem: EtreeElement) -> BoundingBox:
    r"""Get bounding box around a single element.

    :param inkscape: path to an inkscape executable on your local file system
        IMPORTANT: path cannot end with ``.exe``.
        Use something like ``"C:\\Program Files\\Inkscape\\inkscape"``
    :param elem: xml element
    :return: a BoundingBox instance around a single elem
    """
    return get_bounding_boxes(inkscape, elem)[0]


def clear_svg_ultralight_cache() -> None:
    """Clear all cached bounding boxes."""
    for cache_file in _CACHE_DIR.glob("*"):
        cache_file.unlink()


def pad_text(
    inkscape: str | Path, text_elem: EtreeElement, capline_reference_char: str = "M"
) -> PaddedText:
    r"""Create a PaddedText instance from a text element.

    :param inkscape: path to an inkscape executable on your local file system
        IMPORTANT: path cannot end with ``.exe``.
        Use something like ``"C:\\Program Files\\Inkscape\\inkscape"``
    :param text_elem: an etree element with a text tag
    :param capline_reference_char: a character to use to determine the baseline and
        capline. The default "M" is a good choice, but you might need something else
        if using a weird font, or if you'd like to use the x-height instead of the
        capline.
    :return: a PaddedText instance
    """
    rmargin_ref = deepcopy(text_elem)
    capline_ref = deepcopy(text_elem)
    _ = rmargin_ref.attrib.pop("id", None)
    _ = capline_ref.attrib.pop("id", None)
    rmargin_ref.attrib["text-anchor"] = "end"
    capline_ref.text = capline_reference_char

    bboxes = get_bounding_boxes(inkscape, text_elem, rmargin_ref, capline_ref)
    bbox, rmargin_bbox, capline_bbox = bboxes

    tpad = bbox.y - capline_bbox.y
    rpad = -rmargin_bbox.x2
    bpad = capline_bbox.y2 - bbox.y2
    lpad = bbox.x
    return PaddedText(text_elem, bbox, tpad, rpad, bpad, lpad)
