"""Import an svg file as a BoundElement.

:author: Shay Hill
:created: 2024-05-28
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lxml import etree

from svg_ultralight.bounding_boxes.type_bound_element import BoundElement
from svg_ultralight.bounding_boxes.type_bounding_box import BoundingBox
from svg_ultralight.constructors import new_element

if TYPE_CHECKING:
    import os

    from lxml.etree import _Element as EtreeElement  # type: ignore


def _get_bounds_from_viewbox(root: EtreeElement) -> BoundingBox:
    """Get the BoundingBox from the viewbox attribute of the root element.

    :param root: The root element of the svg.
    :return: The BoundingBox of the svg.
    """
    viewbox = root.attrib.get("viewBox")
    if viewbox is None:
        msg = "SVG file has no viewBox attribute. Failed to create BoundingBox."
        raise ValueError(msg)
    x, y, width, height = map(float, viewbox.split())
    return BoundingBox(x, y, width, height)


def import_svg(svg: str | os.PathLike[str]) -> BoundElement:
    """Import an svg file as a BoundElement.

    :param svg: The path to the svg file.
    :return: The BoundElement representation of the svg.

    The viewbox of the svg is used to create the BoundingBox of the BoundElement.
    """
    tree = etree.parse(svg)
    root = tree.getroot()
    bbox = _get_bounds_from_viewbox(root)
    root_as_elem = new_element("g")
    root_as_elem.extend(root)
    return BoundElement(root_as_elem, bbox)
