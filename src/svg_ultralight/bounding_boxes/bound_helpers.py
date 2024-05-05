"""Helper functions for dealing with BoundElements.

:author: Shay Hill
:created: 2024-05-03
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml.etree import _Element as EtreeElement  # type: ignore

from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.bounding_boxes.type_padded_text import PaddedText
from svg_ultralight.constructors import new_element

if TYPE_CHECKING:
    from svg_ultralight.bounding_boxes.supports_bounds import SupportsBounds

_Matrix = tuple[float, float, float, float, float, float]


def new_element_union(
    *elems: EtreeElement | SupportsBounds, **attributes: float | str
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
    bboxes: list[BoundingBox] = []
    for blem in blems:
        if isinstance(blem, BoundingBox):
            bboxes.append(blem)
        elif isinstance(blem, BoundElement):
            bboxes.append(blem.bbox)
        elif isinstance(blem, PaddedText):
            bboxes.append(blem.padded_bbox)

    if not bboxes:
        msg = (
            "Cannot find any bounding boxes to union. "
            + "At least one argument must be a "
            + "BoundElement, BoundingBox, or PaddedText."
        )
        raise ValueError(msg)

    return BoundingBox.merged(*bboxes)


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
