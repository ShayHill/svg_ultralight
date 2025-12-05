"""Helper functions for dealing with BoundElements.

:author: Shay Hill
:created: 2024-05-03
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml import etree
from lxml.etree import _Element as EtreeElement  # pyright: ignore[reportPrivateUsage]

from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds
from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox, HasBoundingBox
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.constructors import new_element
from svg_ultralight.layout import expand_pad_arg
from svg_ultralight.unit_conversion import MeasurementArg, to_user_units

if TYPE_CHECKING:
    import os
    from collections.abc import Sequence

    from svg_ultralight.attrib_hints import ElemAttrib
    from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds

_Matrix = tuple[float, float, float, float, float, float]


def new_element_union(
    *elems: EtreeElement | SupportsBounds, **attributes: ElemAttrib
) -> EtreeElement:
    """Get the union of any elements found in the given arguments.

    :param elems: BoundElements, PaddedTexts, or EtreeElements.
        Other arguments will be ignored.
    :return: a new group element containing all elements.

    This does not support consolidating attributes. E.g., if all elements have the
    same fill color, this will not be recognized and consilidated into a single
    attribute for the group. Too many attributes change their behavior when applied
    to a group.
    """
    elements_found: list[EtreeElement] = []
    for elem in elems:
        if isinstance(elem, (BoundElement, PaddedText)):
            elements_found.append(elem.elem)
        elif isinstance(elem, EtreeElement):
            elements_found.append(elem)

    if not elements_found:
        msg = (
            "Cannot find any elements to union. "
            + "At least one argument must be a "
            + "BoundElement, PaddedText, or EtreeElement."
        )
        raise ValueError(msg)
    group = new_element("g", **attributes)
    group.extend(elements_found)
    return group


def new_bbox_union(*blems: SupportsBounds | EtreeElement) -> BoundingBox:
    """Get the union of the bounding boxes of the given elements.

    :param blems: BoundElements, BoundingBoxes, or PaddedTexts.
        Other arguments will be ignored.
    :return: the union of all bounding boxes as a BoundingBox instance.

    Will used the padded_box attribute of PaddedText instances.
    """
    bboxes = [x.bbox for x in blems if isinstance(x, HasBoundingBox)]
    if not bboxes:
        msg = (
            "Cannot find any bounding boxes to union. "
            + "At least one argument must be a "
            + "BoundElement, BoundingBox, or PaddedText."
        )
        raise ValueError(msg)

    return BoundingBox.union(*bboxes)


def new_bound_union(*blems: SupportsBounds | EtreeElement) -> BoundElement:
    """Get the union of the bounding boxes of the given elements.

    :param blems: BoundElements or EtreeElements.
        At least one argument must be a BoundElement, BoundingBox, or PaddedText.
    :return: the union of all arguments as a BoundElement instance.

    Will used the padded_box attribute of PaddedText instances.
    """
    group = new_element_union(*blems)
    bbox = new_bbox_union(*blems)
    return BoundElement(group, bbox)


def cut_bbox(
    bbox: SupportsBounds,
    *,
    x: float | None = None,
    y: float | None = None,
    x2: float | None = None,
    y2: float | None = None,
) -> BoundingBox:
    """Return a new bounding box with updated limits.

    :param bbox: the original bounding box or bounded element.
    :param x: the new x-coordinate.
    :param y: the new y-coordinate.
    :param x2: the new x2-coordinate.
    :param y2: the new y2-coordinate.
    :return: a new bounding box with the updated limits.
    """
    x = bbox.x if x is None else x
    y = bbox.y if y is None else y
    x2 = bbox.x2 if x2 is None else x2
    y2 = bbox.y2 if y2 is None else y2
    x, x2 = sorted((x, x2))
    y, y2 = sorted((y, y2))
    width = x2 - x
    height = y2 - y
    return BoundingBox(x, y, width, height)


def pad_bbox(
    bbox: SupportsBounds, pad: MeasurementArg | Sequence[MeasurementArg]
) -> BoundingBox:
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
    if len(root) == 0:
        msg = "SVG file does not contain any elements."
        raise ValueError(msg)
    elem = new_element("g")
    elem.extend(list(root))
    if len(elem) == 1:
        elem = elem[0]
    bbox = BoundingBox(*get_bounding_box_from_root(root))
    return BoundElement(elem, bbox)
