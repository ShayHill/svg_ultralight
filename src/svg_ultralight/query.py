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
from typing import TYPE_CHECKING, Literal
from warnings import warn

from lxml import etree

from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.constructors import update_element
from svg_ultralight.font_tools.font_info import get_svg_font_attributes
from svg_ultralight.main import new_svg_root, write_svg

if TYPE_CHECKING:
    from collections.abc import Iterator

    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )


with TemporaryFile() as f:
    _CACHE_DIR = Path(f.name).parent / "svg_ultralight_cache"

_CACHE_DIR.mkdir(exist_ok=True)

_TEMP_ID_PREFIX = "svg_ultralight-temp_query_module-"


def _iter_elems(*elem_args: EtreeElement) -> Iterator[EtreeElement]:
    """Yield element and sub-elements."""
    for elem in elem_args:
        yield from elem.iter()


def _fill_ids(*elem_args: EtreeElement) -> None:
    """Set the id attribute of an element and all its children. Keep existing ids.

    :param elem: an etree element, accepts multiple arguments
    """
    for elem in _iter_elems(*elem_args):
        if elem.get("id") is None:
            elem.set("id", f"{_TEMP_ID_PREFIX}-{uuid.uuid4()}")


def _normalize_views(elem: EtreeElement) -> None:
    """Create a square viewBox for any element with an svg tag.

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


def _split_bb_string(bb_string: str) -> tuple[str, BoundingBox]:
    """Split a bounding box string into id and BoundingBox instance.

    :param bb_string: "id,x,y,width,height"
    :return: (id, BoundingBox(x, y, width, height))
    """
    id_, *bounds = bb_string.split(",")
    x, y, width, height = (float(x) for x in bounds)
    return id_, BoundingBox(x, y, width, height)


def map_elems_to_bounding_boxes(
    inkscape: str | os.PathLike[str], *elem_args: EtreeElement
) -> dict[EtreeElement | Literal["svg"], BoundingBox]:
    r"""Query an svg file for bounding-box dimensions.

    :param inkscape: path to an inkscape executable on your local file system
        IMPORTANT: path cannot end with ``.exe``.
        Use something like ``"C:\\Program Files\\Inkscape\\inkscape"``
    :param elem_args: xml element (written to a temporary file then queried)
    :return: input svg elements and any descendents of those elements mapped
        `BoundingBox(x, y, width, height)`
        So return dict keys are the input elements themselves with one exception: a
        string key, "svg", is mapped to a bounding box around all input elements.
    :effects: temporarily adds an id attribute if any ids are missing. These are
        removed if the function completes. Existing, non-unique ids will break this
        function.

    Bounding boxes are relative to svg viewBox. If, for instance, viewBox x == -10,
    all bounding-box x values will be offset -10. So, everything is wrapped in a root
    element, `envelope` with a "normalized" viewBox, `viewBox=(0, 0, 1, 1)`. That
    way, any child root elements ("child root elements" sounds wrong, but it works)
    viewBoxes are normalized as well. This works even with a root element around a
    root element, so input elem_args can be root elements or "normal" elements like
    "rect", "circle", or "text" or a mixture of both. Bounding boxes output here will
    work as expected in any viewBox.

    The ``inkscape --query-all svg`` call will return a tuple:

    (b'svg1,x,y,width,height\\r\\elem1,x,y,width,height\\r\\n', None)
    where x, y, width, and height are strings of numbers.

    This calls the command and formats the output into a dictionary. There is a
    little extra complexity to handle cases with duplicate elements. Inkscape will
    map bounding boxes to element ids *if* those ids are unique. If Inkscape
    encounters a duplicate ID, Inkscape will map the bounding box of that element to
    a string like "rect1". If you pass unequal elements with the same id, I can't
    help you, but you might pass the same element multiple times. If you do this,
    Inkscape will find a bounding box for each occurrence, map the first occurrence
    to the id, then map subsequent occurrences to a string like "rect1". This
    function will handle that.
    """
    if not elem_args:
        return {}
    _fill_ids(*elem_args)

    envelope = _envelop_copies(*elem_args)
    with NamedTemporaryFile(mode="wb", delete=False, suffix=".svg") as svg_file:
        svg = write_svg(svg_file, envelope)
    with Popen(f'"{inkscape}" --query-all {svg}', stdout=PIPE) as bb_process:
        bb_data = str(bb_process.communicate()[0])[2:-1]
    os.unlink(svg_file.name)

    bb_strings = re.split(r"[\\r]*\\n", bb_data)[:-1]
    id2bbox = dict(map(_split_bb_string, bb_strings))

    elem2bbox: dict[EtreeElement | Literal["svg"], BoundingBox] = {}
    for elem in _iter_elems(*elem_args):
        elem_id = elem.attrib.get("id")
        if not (elem_id):  # id removed in a previous loop
            continue
        with suppress(KeyError):
            # some elems like <style> don't have a bounding box
            elem2bbox[elem] = id2bbox[elem_id]
        if elem_id.startswith(_TEMP_ID_PREFIX):
            del elem.attrib["id"]
    elem2bbox["svg"] = BoundingBox.merged(*id2bbox.values())
    return elem2bbox


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
    inkscape: str | os.PathLike[str], *elem_args: EtreeElement
) -> tuple[BoundingBox, ...]:
    r"""Get bounding box around a single element (or multiple elements).

    :param inkscape: path to an inkscape executable on your local file system
        IMPORTANT: path cannot end with ``.exe``.
        Use something like ``"C:\\Program Files\\Inkscape\\inkscape"``
    :param elem_args: xml elements
    :return: a BoundingBox instance around a each elem_arg

    This will work most of the time, but if you're missing an nsmap, you'll need to
    create an entire xml file with a custom nsmap (using
    `svg_ultralight.new_svg_root`) then call `map_elems_to_bounding_boxes` directly.
    """
    elem2hash = {elem: _hash_elem(elem) for elem in elem_args}
    cached = [_try_bbox_cache(h) for h in elem2hash.values()]
    if None not in cached:
        return tuple(filter(None, cached))

    hash2bbox = {h: c for h, c in zip(elem2hash.values(), cached) if c is not None}
    remainder = [e for e, c in zip(elem_args, cached) if c is None]
    id2bbox = map_elems_to_bounding_boxes(inkscape, *remainder)
    for elem in remainder:
        hash_ = elem2hash[elem]
        hash2bbox[hash_] = id2bbox[elem]
        with (_CACHE_DIR / hash_).open("wb") as f:
            pickle.dump(hash2bbox[hash_], f)
    return tuple(hash2bbox[h] for h in elem2hash.values())


def get_bounding_box(
    inkscape: str | os.PathLike[str], elem: EtreeElement
) -> BoundingBox:
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


DEFAULT_Y_BOUNDS_REFERENCE = "{[|gjpqyf"


def pad_text(
    inkscape: str | os.PathLike[str],
    text_elem: EtreeElement,
    y_bounds_reference: str = DEFAULT_Y_BOUNDS_REFERENCE,
    *,
    font: str | os.PathLike[str] | None = None,
) -> PaddedText:
    r"""Create a PaddedText instance from a text element.

    :param inkscape: path to an inkscape executable on your local file system
        IMPORTANT: path cannot end with ``.exe``.
        Use something like ``"C:\\Program Files\\Inkscape\\inkscape"``
    :param text_elem: an etree element with a text tag
    :param y_bounds_reference: an optional string to use to determine the ascent and
        capline of the font. The default is a good choice, which approaches or even
        meets the ascent of descent of most fonts without using utf-8 characters. You
        might want to use a letter like "M" or even "x" if you are using an all-caps
        string and want to center between the capline and baseline or if you'd like
        to center between the baseline and x-line.
    :param font: optionally add a path to a font file to use for the text element.
        This is going to conflict with any font-family, font-style, or other
        font-related attributes *except* font-size. You likely want to use
        `font_tools.new_padded_text` if you're going to pass a font path, but you can
        use it here to compare results between `pad_text` and `new_padded_text`.
    :return: a PaddedText instance
    """
    if font is not None:
        _ = update_element(text_elem, **get_svg_font_attributes(font))
    rmargin_ref = deepcopy(text_elem)
    capline_ref = deepcopy(text_elem)
    _ = rmargin_ref.attrib.pop("id", None)
    _ = capline_ref.attrib.pop("id", None)
    rmargin_ref.attrib["text-anchor"] = "end"
    capline_ref.text = y_bounds_reference

    bboxes = get_bounding_boxes(inkscape, text_elem, rmargin_ref, capline_ref)
    bbox, rmargin_bbox, capline_bbox = bboxes

    tpad = bbox.y - capline_bbox.y
    rpad = -rmargin_bbox.x2
    bpad = capline_bbox.y2 - bbox.y2
    lpad = bbox.x
    return PaddedText(text_elem, bbox, tpad, rpad, bpad, lpad)
