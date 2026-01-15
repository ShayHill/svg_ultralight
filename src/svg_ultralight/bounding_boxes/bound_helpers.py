"""Helper functions for dealing with BoundElements.

Parsing an existing svg file into a BoundElement will replace any `use` elements
with the elements they use *if the used element is a `path`*, remove the used
elements if they were only defs, then clean up
 and empty defs sections.

This is the most straightforward way to simplify optimization (finding paths that can be
copied) when the same BoundElement is written into another file with write_svg.

:author: Shay Hill
:created: 2024-05-03
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from lxml import etree
from paragraphs import par

from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds
from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox, HasBoundingBox
from svg_ultralight.constructors import new_element, update_element
from svg_ultralight.constructors.new_element import new_element_union
from svg_ultralight.layout import PadArg, expand_pad_arg
from svg_ultralight.unit_conversion import MeasurementArg, to_user_units
from lxml.etree import _Comment as EtreeComment  # pyright: ignore[reportPrivateUsage]

if TYPE_CHECKING:
    import os

    from lxml.etree import (
        _Element as EtreeElement,  # pyright: ignore[reportPrivateUsage]
    )

    from svg_ultralight.attrib_hints import ElemAttrib
    from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds

_Matrix = tuple[float, float, float, float, float, float]


def new_bbox_union(*blems: SupportsBounds | EtreeElement) -> BoundingBox:
    """Get the union of the bounding boxes of the given elements.

    :param blems: BoundElements, BoundingBoxes, or PaddedTexts.
        Other arguments will be ignored.
    :return: the union of all bounding boxes as a BoundingBox instance.

    Will used the padded_box attribute of PaddedText instances.
    """
    bboxes = [x.bbox for x in blems if isinstance(x, HasBoundingBox)]
    if not bboxes:
        msg = par(
            """Cannot find any bounding boxes to union. At least one argument
            must be a BoundElement, BoundingBox, or PaddedText."""
        )
        raise ValueError(msg)

    return BoundingBox.union(*bboxes)


def new_bound_union(
    *blems: SupportsBounds | EtreeElement, **attribs: ElemAttrib
) -> BoundElement:
    """Get the union of the bounding boxes of the given elements.

    :param blems: BoundElements or EtreeElements.
        At least one argument must be a BoundElement, BoundingBox, or PaddedText.
    :return: the union of all arguments as a BoundElement instance.

    Will used the padded_box attribute of PaddedText instances.
    """
    if not blems:
        return BoundElement(new_element("g", **attribs), BoundingBox(0, 0, 0, 0))
    group = new_element_union(*blems, **attribs)
    bbox = new_bbox_union(*blems)
    return BoundElement(group, bbox)


def cut_bbox(
    bbox: SupportsBounds,
    *,
    x: MeasurementArg | None = None,
    y: MeasurementArg | None = None,
    x2: MeasurementArg | None = None,
    y2: MeasurementArg | None = None,
) -> BoundingBox:
    """Return a new bounding box with updated limits.

    :param bbox: the original bounding box or bounded element.
    :param x: the new x-coordinate.
    :param y: the new y-coordinate.
    :param x2: the new x2-coordinate.
    :param y2: the new y2-coordinate.
    :return: a new bounding box with the updated limits.
    """
    x = bbox.x if x is None else to_user_units(x)
    y = bbox.y if y is None else to_user_units(y)
    x2 = bbox.x2 if x2 is None else to_user_units(x2)
    y2 = bbox.y2 if y2 is None else to_user_units(y2)
    x, x2 = sorted((x, x2))
    y, y2 = sorted((y, y2))
    width = x2 - x
    height = y2 - y
    return BoundingBox(x, y, width, height)


def pad_bbox(bbox: SupportsBounds, pad: PadArg) -> BoundingBox:
    """Return a new bounding box with padding.

    :param bbox: the original bounding box or bounded element.
    :param pad: the padding to apply.
        If a single number, the same padding will be applied to all sides.
        If a tuple, will be applied per css rules.
        len = 1 : 0, 0, 0, 0
        len = 2 : 0, 1, 0, 1
        len = 3 : 0, 1, 2, 1
        len = 4 : 0, 1, 2, 3
    :return: a new bounding box with padding applied.
    """
    top, right, bottom, left = expand_pad_arg(pad)
    return cut_bbox(
        bbox, x=bbox.x - left, y=bbox.y - top, x2=bbox.x2 + right, y2=bbox.y2 + bottom
    )


def bbox_dict(bbox: SupportsBounds) -> dict[str, float]:
    """Return a dictionary representation of a bounding box.

    :param bbox: the bounding box or bound element from which to extract dimensions.
    :return: a dictionary with keys x, y, width, and height.
    """
    return {"x": bbox.x, "y": bbox.y, "width": bbox.width, "height": bbox.height}


def new_bbox_rect(bbox: BoundingBox, **kwargs: ElemAttrib) -> EtreeElement:
    """Return a new rect element with the same dimensions as the bounding box.

    :param bbox: the bounding box or bound element from which to extract dimensions.
    :param kwargs: additional attributes for the rect element.
    """
    return new_element("rect", **bbox_dict(bbox), **kwargs)


def new_bound_rect(bbox: BoundingBox, **kwargs: ElemAttrib) -> BoundElement:
    """Return a new rect element with the same dimensions as the bounding box.

    :param bbox: the bounding box or bound element from which to extract dimensions.
    :param kwargs: additional attributes for the rect element.
    """
    elem = new_bbox_rect(bbox, **kwargs)
    return BoundElement(elem, bbox)


def get_bounding_box_from_root(
    elem: EtreeElement,
) -> tuple[float, float, MeasurementArg, MeasurementArg]:
    """Return the view box of an element as a tuple of floats.

    :param elem: the element from which to extract the view box.
    :return: a tuple of floats representing the view box.

    This will work on svg files created by this library and some others. Not all svg
    files have a viewBox attribute.
    """
    view_box = elem.get("viewBox")
    if view_box:
        x, y, width, height = map(float, view_box.split())
        return x, y, width, height
    width = elem.get("width")
    height = elem.get("height")
    if width is None or height is None:
        msg = "Cannot infer viewBox from element."
        raise ValueError(msg)
    return 0, 0, to_user_units(width), to_user_units(height)


def parse_bound_element(svg_file: str | os.PathLike[str]) -> BoundElement:
    """Import an element as a BoundElement.

    :param elem: the element to import.
    :return: a BoundElement instance.
    :raises ValueError: if the SVG file does not contain any elements.

    This will work on any svg file that has a root element with a viewBox attribute.
    That's any svg created by this library and most others.
    """
    tree = etree.parse(svg_file)
    root = tree.getroot()
    _remove_namespace_prefixes(root)
    if len(root) == 0:
        msg = "SVG file does not contain any elements."
        raise ValueError(msg)
    _decopy_paths(root)
    elem = new_element("g")
    elem.extend(list(root))
    if len(elem) == 1:
        elem = elem[0]
    bbox = BoundingBox(*get_bounding_box_from_root(root))
    return BoundElement(elem, bbox)


def _remove_namespace_prefixes(root: EtreeElement) -> None:
    """Remove namespace prefixes from the root element and its attributes."""
    for elem in root.iter():
        if isinstance(elem, EtreeComment):
            continue
        elem.tag = etree.QName(elem).localname
        # Process attributes with namespace prefixes (e.g., xlink:href -> href)
        for key in list(elem.attrib.keys()):
            if ":" in key:
                localname = etree.QName(key).localname
                elem.attrib[localname] = elem.attrib.pop(key)


def _combine_use_and_def(use_elem: EtreeElement, def_elem: EtreeElement) -> EtreeElement:
    """Combine a use element and a defd path element.
    
    :param use: a use element that used a defd path element.
    :param defd_path: the defd path element
    :return: The combined element.
    """
    def_attrib = {k: v for k, v in def_elem.attrib.items() if k != "id"}
    use_attrib = {k: v for k, v in use_elem.attrib.items() if k != "href"}
    if not use_attrib:
        return new_element("path", **def_attrib)
    if not def_attrib:
        return new_element("path", **use_attrib)
    for key, val in tuple(use_attrib.items()):
        if key in ("x", "y", "width", "height"):
            _ = use_attrib.pop(key)
            def_attrib[key] = val
    if not use_attrib:
        return new_element("path", **def_attrib)
    new_elem = new_element("g", **use_attrib)
    new_elem.append(update_element(def_elem, **def_attrib))
    return new_elem
def _decopy_paths(root: EtreeElement) -> None:
    """Replace use elements with the elements they use."""
    hrefs: set[str] = set()
    for use_elem in root.xpath('.//*[local-name() = "use"]'):
        href = _get_href(use_elem)
        original = _find_href(root, href)
        if etree.QName(original).localname != "path":
            continue
        def_elem = copy.deepcopy(original)
        new_elem = _combine_use_and_def(use_elem, def_elem)
        _replace_use(use_elem, new_elem)
        hrefs.add(href)

    _remove_no_longer_referenced_defs(root, hrefs)
    _remove_empty_defs(root)


def _get_href(use: EtreeElement) -> str:
    """Get the href of a use element."""
    href = use.get("href")
    if href is None:
        msg = "Use element has no href attribute."
        raise ValueError(msg)
    return href.lstrip("#")


def _find_href(root: EtreeElement, href: str) -> EtreeElement:
    """Find the element with the given href."""
    referenced = root.xpath(f'.//*[@id = "{href}"]')
    return referenced[0]


def _replace_use(use: EtreeElement, new_elem: EtreeElement) -> None:
    """Replace a use element with a new element."""
    parent = use.getparent()
    if parent is None:
        msg = "Use element has no parent."
        raise RuntimeError(msg)
    parent.replace(use, new_elem)


def _remove_no_longer_referenced_defs(root: EtreeElement, hrefs: set[str]) -> None:
    """Remove defs elements that are no longer referenced."""
    for href in hrefs:
        original = _find_href(root, href)
        parent = original.getparent()
        if parent is None:
            msg = "Referenced element has no parent."
            raise RuntimeError(msg)
        if etree.QName(parent).localname == "defs":
            parent.remove(original)


def _remove_empty_defs(root: EtreeElement) -> None:
    """Remove defs elements that are empty."""
    for defs in root.xpath('.//*[local-name() = "defs"]'):
        if len(defs) == 0:
            parent = defs.getparent()
            if parent is None:
                msg = "Defs element has no parent."
                raise RuntimeError(msg)
            parent.remove(defs)
